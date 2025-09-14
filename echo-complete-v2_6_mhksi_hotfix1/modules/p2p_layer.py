import os, json, asyncio
from datetime import datetime, timedelta

try:
    from kademlia.network import Server
    KADEMLIA_AVAILABLE = True
except Exception:
    KADEMLIA_AVAILABLE = False
    Server = object  # placeholder

PEERS_FILE = "peers.json"
RETRY_LIMIT = 3
CLEANUP_DAYS = 30

class P2PLayer:
    def __init__(self, host, port, bootstrap_nodes, node_id):
        self.host = host; self.port = port; self.bootstrap_nodes = bootstrap_nodes
        self.node_id = node_id
        self.loop = None
        if KADEMLIA_AVAILABLE:
            self.server = Server()
        else:
            self.server = None

    async def _start(self):
        if not KADEMLIA_AVAILABLE: return
        await self.server.listen(self.port, interface=self.host)
        if self.bootstrap_nodes:
            try: await self.server.bootstrap(self.bootstrap_nodes)
            except Exception: pass

    def run(self):
        if not KADEMLIA_AVAILABLE: return
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._start())
        try: self.loop.run_forever()
        finally: self.loop.close()

def load_peers():
    if not os.path.exists(PEERS_FILE): return []
    try:
        peers = json.load(open(PEERS_FILE))
        out=[]; now=datetime.utcnow()
        for p in peers:
            try:
                ls=datetime.fromisoformat(p.get("last_seen"))
                if (now-ls) <= timedelta(days=CLEANUP_DAYS): out.append(p)
            except Exception: pass
        return out
    except Exception: return []

def save_peers(peers):
    try: json.dump(peers, open(PEERS_FILE, "w"), indent=2)
    except Exception: pass

def update_peer_status(node_id, status, host=None, port=None):
    peers = load_peers()
    now = datetime.utcnow().isoformat()
    found=False
    for p in peers:
        if p.get("node_id")==node_id:
            p["status"]=status
            if status=="active": p["last_seen"]=now; p["retries"]=0
            else: p["retries"]=p.get("retries",0)+1
            if host: p["host"]=host
            if port: p["port"]=port
            found=True; break
    if not found and status=="active" and host and port:
        peers.append({"node_id":node_id,"host":host,"port":port,"status":"active","last_seen":now,"retries":0})
    peers = [p for p in peers if p.get("retries",0) <= RETRY_LIMIT]
    save_peers(peers)

def cleanup_peers(days=CLEANUP_DAYS):
    peers = load_peers()
    now = datetime.utcnow()
    keep = []
    for p in peers:
        try:
            ls = datetime.fromisoformat(p.get("last_seen", now.isoformat()))
            if (now - ls).days <= days:
                keep.append(p)
        except Exception:
            pass
    save_peers(keep)
