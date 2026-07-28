import asyncio
import threading
import torch
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from app.schemas.train_schema import TrainRequest
from app.core.model import BigramLanguageModel
from app.core.trainer import Trainer
from app.core.generator import Generator
from app.utils.tokenizer import Tokenizer
from app.api.websocket import manager
from app.state import state


'''
    uvicorn starts
    → creates the asyncio event loop
    → starts FastAPI inside that loop
    → all async def routes run as coroutines on that loop
'''

router = APIRouter()
'''
    Main thread
    └── asyncio event loop        ← _loop points to this
        └── FastAPI / WebSockets / all async code
        
    AbstractEventLoop is just the base class / interface that defines what an event loop must be able to do
    —> run_forever(), call_soon(), create_task() etc.
'''
_loop: asyncio.AbstractEventLoop = None  # reference to that event loop not the thread

CORPUS_DIR = Path("training_data_corpus")

@router.get("/datasets")
async def list_datasets():
    if not CORPUS_DIR.exists():
        return {"datasets": []}
    files = [
        {"name": f.name, "size_kb": round(f.stat().st_size / 1024, 1)}
        for f in sorted(CORPUS_DIR.glob("*.txt"))
    ]
    return {"datasets": files}

@router.post("/upload-default")
async def upload_default(filename: str):
    path = CORPUS_DIR / filename
    if not path.exists() or path.suffix != ".txt":
        raise HTTPException(400, "File not found")
    text = path.read_text(encoding="utf-8")
    state.text = text
    state.tokenizer = Tokenizer(text)
    return {"vocab_size": state.tokenizer.vocab_size, "chars": len(text), "name": filename}

@router.post("/upload")
async def upload(file:UploadFile = File(...)):
    content = await file.read()
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(400, "File must be valid UTF-8 text")
    if len(text) < 100:
        raise HTTPException(400, "File too short")
    
    print("File uploaded successfully")

    state.text = text
    state.tokenizer = Tokenizer(text)
    return {"vocab_size" : state.tokenizer.vocab_size, "chars" : len(text)}

@router.post("/train")
async def train(req:TrainRequest):                             # already running ON the event loop (Uvicorn started it)
    if state.text is None:
        raise HTTPException(400, "Upload a text file first")
    if state.training:                                             
        raise HTTPException(400, "Training already running")   # preventing 2 training jobs, from running simultaneously

    print("Training request initiated ... ")
    global _loop
    '''
    Uvicorn starts loop
    → loop runs async def train()
        → asyncio.get_event_loop()  ← returns the same loop we're already on
        → stored in _loop
    → threading.Thread starts (training)
        → thread has no loop
        → uses _loop to send work back
    '''
    _loop = asyncio.get_event_loop()                           # fetches a reference to the currently running event loop

    device      = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer   = state.tokenizer
    data        = tokenizer.to_tensor(state.text)
    n           = int(0.9 * len(data))

    model = BigramLanguageModel(
        vocab_size  = tokenizer.vocab_size,
        n_embd      = req.n_embd,
        n_head      = req.n_head,
        n_layer     = req.n_layer,
        block_size  = req.block_size,
        dropout     = req.dropout,
        device      = device,
    ).to(device)

    state.model       = model
    state.generator   = Generator(model, tokenizer, device)
    state.training    = True

    trainer = Trainer(
        model         = model,
        train_data    = data[:n],
        val_data      = data[n:],
        block_size    = req.block_size,
        batch_size    = req.batch_size,
        learning_rate = req.learning_rate,
        eval_iters    = 100,
        device        = device,
    )

    def on_eval(epoch: int, train_loss: float, val_loss: float):
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({"type": "loss", "epoch": epoch, "train_loss": round(train_loss, 4), "val_loss": round(val_loss, 4)}),
            _loop,
        )
        text = state.generator.generate(max_new_tokens=200)
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({"type": "text", "text": text}),
            _loop,
        )

    def run():
        try:
            trainer.train(
                max_iters      = req.max_iters,
                eval_interval  = req.eval_interval,
                on_eval        = on_eval,
            )
        finally:
            state.training = False
            asyncio.run_coroutine_threadsafe(
                manager.broadcast({'type' : 'done'}),
                _loop,
            )

    threading.Thread(target=run, daemon=True).start()
    return {"status" : "training started", "device":device}

@router.get("/generate")
async def generate(max_new_tokens: int = 500):
    if state.generator is None:
        raise HTTPException(400, "No model availabel")
    return {"text" : state.generator.generate(max_new_tokens)}

@router.get("/status")
async def status():
    return {
        "training":   state.training,
        "has_model":  state.model is not None,
        "has_text":   state.text is not None,
        "vocab_size": state.tokenizer.vocab_size if state.tokenizer else None,
    }

@router.websocket('/ws/loss')
async def websocket_loss(ws: WebSocket):
    '''This is where the browser connects when training starts:'''
    await manager.connect(ws)
    try:
        while True:
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)