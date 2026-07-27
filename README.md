## Running the Application locally

### Start (detached — terminal can be closed)
```bash
docker compose up --build -d
```

### View logs / print statements separate terminal
```bash
docker compose logs -f app
```
`-f` follows live logs. Press `Ctrl+C` to exit - the container keeps running.

### View nginx logs
```bash
docker compose logs nginx
```

### Stop the container (keeps images)
```bash
docker compose stop
```

### Start again (no rebuild)
```bash
docker compose start
```

### Delete this project's containers, images, and network
```bash
docker compose down --rmi local
```

### Run locally (without Docker)
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Access the app
Open [http://localhost/](http://localhost/) in your web browser.

### Rebuilding
If you need to rebuild after making changes:
```bash
docker compose down
docker compose up --build -d
```

---

### Command reference

| Command | Effect |
|---|---|
| `down` | Stops and removes containers and network. Images stay on disk. |
| `down --rmi local` | Same as above, plus removes images built from this project's Dockerfile only. Frees disk space, but the next `up --build` will download/build everything again. Other Docker images are left untouched. |