
## FastAPI — Async, Event Loop & Threading

### Key Terms

| Term | Definition |
|---|---|
| **Blocking** | Main thread occupied with a heavy task, unable to respond to anything else |
| **Thread** | An independent worker executing code |
| **Event Loop** | A single thread that switches between tasks at every `await` |
| **asyncio** | Python stdlib that provides the event loop, `async`/`await`, and `run_coroutine_threadsafe` |
| **Coroutine** | An `async def` function that can pause at `await` and resume later |
| **Daemon Thread** | A background thread that dies automatically when the main thread dies |

---

### How the Event Loop Works

When FastAPI starts, the OS creates a Python process with one main thread. That main thread starts the asyncio event loop and runs it forever.

```
OS starts Python process
→ creates Main Thread
→ Main Thread starts asyncio event loop
→ event loop runs forever: accepts HTTP, handles WebSockets, serves responses
```

The event loop is literally this:

```
while server is running:
    look at all pending tasks
    pick one that is ready
    run it until it hits an "await"
    put it back, pick the next ready task
    repeat
```

One thread switching between tasks so fast it looks like everything is happening simultaneously. It never gets blocked by slow I/O it just context-switches to the next ready task at every `await`.

### async / await

- `async def` marks a function as a **coroutine** - it can be paused and resumed
- `await` is the pause point - "I'm waiting for this, event loop go serve someone else"
- The **coroutine** waits at the `await` line - not the thread
- The **thread** (event loop) keeps running other coroutines
- When the awaited thing completes, the event loop resumes the paused coroutine

```python
async def handle_request():
    data = await read_from_socket()   # coroutine pauses here
                                      # event loop runs other tasks
    return data
```

---

## Main Thread vs Background Thread
### The Problem

Training a model takes minutes or hours. If the event loop runs the training:

- No `await` inside the training loop pure CPU/GPU math
- Event loop gets stuck - cannot context switch
- No HTTP requests answered, no WebSocket messages sent
- Server appears completely frozen

### The Solution - Background Thread

Spawn a second worker (background thread) to do the heavy lifting.

```
Main Thread (event loop)  →  handles HTTP, WebSocket, /status, /generate
Background Thread         →  runs training loop, crunches GPU math
```

The background thread is:
- Spawned **by** the main thread when `/train` is called
- A plain regular Python thread no `async`, no `await`, no event loop
- Independently running after spawn, main thread doesn't wait for it
- Connected to the main thread only via **shared memory** (`state`, `_loop`)

### Shared Memory

Both threads live in the same Python process - same RAM. They share:
- `state.model` - the model being trained
- `state.training` - training flag
- `_loop` - reference to the main thread's event loop

No copying. No serialization. Background thread writes a value, main thread reads it directly from the same memory address.

> **Race condition note:** shared memory is safe here because the background thread writes to `state` and the main thread only reads it. They don't write to the same variable simultaneously no locks needed.

---

## Sending Updates Every N Epochs

### The Problem

Every 200 epochs, the background thread needs to send loss values over WebSocket to the browser.

But:
1. WebSocket operations are `async` - they need an event loop
2. The background thread has no event loop
3. You cannot `await` outside an event loop

```python
# inside background thread — CRASHES
await manager.broadcast(data)       # no event loop here

# inside background thread — ALSO WRONG
asyncio.run(manager.broadcast(data))  # creates a new event loop, conflicts with main loop
```

### The Solution — `run_coroutine_threadsafe`

```python
asyncio.run_coroutine_threadsafe(manager.broadcast(data), _loop)
```

This line does **not** send the message. It does not touch the WebSocket. It does not write any bytes.

It just drops a note in the main thread's event loop queue:

> *"Hey `_loop`, when you're free, please run `broadcast(data)` on yourself."*

The background thread immediately continues training - no pause, no wait.

The main thread's event loop picks up the note at its next cycle, runs `broadcast()`, `await`s the socket write, and sends the bytes to the browser.

```
Background Thread          Main Thread (event loop)
─────────────────          ────────────────────────
training...                listening...
training...
epoch 200 hit
drop note in queue ──────→ picks up note
keep training              runs broadcast()
training...                awaits socket write
training...                bytes sent to browser ✓
training...                back to listening
```

Training never pauses. Fire and forget.

---

## Why `_loop` is Captured at Request Time

```python
@router.post("/train")
async def train(req):
    global _loop
    _loop = asyncio.get_event_loop()   # ← captured here
    ...
    threading.Thread(target=run, daemon=True).start()
```

At this point we are inside an `async def` on the main thread - so `get_event_loop()` returns FastAPI's event loop. We store it in `_loop` so the background thread can reference it later when calling `run_coroutine_threadsafe`. Without this reference, the background thread has no way to reach the main thread's loop.

---

## Full Picture

```
Main Thread (event loop)
├── always running
├── handles all async stuff: HTTP, WebSocket, /status, /generate
└── has a task queue: [task1, task2, ...]
          ↑
          run_coroutine_threadsafe drops tasks here from background thread

Background Thread
├── spawned by main thread when POST /train is called
├── plain Python — for loop, GPU math, no async/await
├── shares memory with main thread (state, _loop)
└── every 200 steps:
    ├── drops broadcast(loss) into main thread's queue   → no pause
    ├── drops broadcast(text) into main thread's queue   → no pause
    └── immediately continues to next training step
```

---

## `daemon=True` - Clean Shutdown

```python
threading.Thread(target=run, daemon=True).start()
```

Without `daemon=True`: pressing Ctrl+C kills the main thread but the background thread keeps running (training could go on for hours) - the process never exits.

With `daemon=True`: when the main thread dies, the background thread is killed immediately. Clean shutdown.

---

## Summary Flow — `/train` Request End to End

```
1. Browser sends POST /train with hyperparams
2. Event loop receives request (async handler)
3. Handler captures _loop = current event loop
4. Handler builds model, trainer, generator → stored in state (shared memory)
5. Handler spawns background thread → returns HTTP 200 immediately
6. Background thread starts training loop (blocking, GPU math)
7. Every 200 steps:
   └── run_coroutine_threadsafe(broadcast(loss), _loop)
   └── run_coroutine_threadsafe(broadcast(text), _loop)
   └── training continues without pause
8. Main thread event loop picks up broadcast tasks → sends WebSocket messages
9. Browser receives messages → updates chart + text panel live
10. Training ends → state.training = False → broadcast("done") → browser notified
```