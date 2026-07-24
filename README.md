## Running the Application

### Start (detached — terminal can be closed)
```bash
docker compose up --build -d
```

### View logs / print statements
```bash
docker compose logs -f app
```
`-f` follows live. `Ctrl+C` to exit — container keeps running.

### View nginx logs
```bash
docker compose logs nginx
```

### Stop (keeps images)
```bash
docker compose stop
```

### Start again (no rebuild)
```bash
docker compose start
```

### Delete this project's containers + images + network
```bash
docker compose down --rmi local
```

run locally 
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

down — stops + removes containers and network. Images stay on disk.

down --rmi local — same as above + also deletes the images built from your Dockerfile. Frees disk space but next up --build downloads/builds everything again.


http://localhost/ on the web browser

if need to do re build 
docker compose down
docker compose up --build -d

> `down` = stop + remove containers and network  
> `--rmi local` = also removes images built from this project's Dockerfile only, leaves all other Docker images untouched