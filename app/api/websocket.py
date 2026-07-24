import asyncio 
import json 
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []       # list of every browser tab currently connected

    async def connect(self, ws: WebSocket):
        '''
            When a browser opens the WebSocket - accept the handshake, add it to the list 
            await - because accepting involves network IO. 
        '''
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):                 
        ''' Browser closed tab or lost connection - remove from list '''
        self.active.remove(ws)                            

    async def broadcast(self, data: dict):
        '''
            Loop every connected browser, send the JSON message to each. 
            If sending fails (tab closed mid-training) - mark it dead, remove from the loop. 
        '''
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(json.dumps(data))      
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active.remove(ws)

manager = ConnectionManager()    # one instance imported everywhere