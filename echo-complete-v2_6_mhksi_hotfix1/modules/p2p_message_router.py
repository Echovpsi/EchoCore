import asyncio, json
try:
    from modules.p2p_layer import P2PLayer, KADEMLIA_AVAILABLE
except Exception:
    P2PLayer = object
    KADEMLIA_AVAILABLE = False

def _ensure_bytes(obj):
    if isinstance(obj,(bytes,bytearray)): return obj
    if isinstance(obj,str): return obj.encode()
    return json.dumps(obj).encode()

class P2PMessageRouter:
    def __init__(self, p2p_layer: P2PLayer):
        self.p2p_layer = p2p_layer

    def send_message(self, topic: str, message: dict):
        if not KADEMLIA_AVAILABLE or not getattr(self.p2p_layer, 'server', None):
            return
        coro = self.p2p_layer.server.set(topic, _ensure_bytes(message))
        asyncio.run_coroutine_threadsafe(coro, self.p2p_layer.loop)

    async def receive_message(self, topic: str):
        if not KADEMLIA_AVAILABLE or not getattr(self.p2p_layer, 'server', None):
            return None
        res = await self.p2p_layer.server.get(topic)
        if res is None: return None
        try:
            s = res.decode() if isinstance(res,(bytes,bytearray)) else res
            return json.loads(s)
        except Exception:
            return None
