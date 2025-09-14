import os, sqlite3, json, hashlib
from datetime import datetime
DDL = """
CREATE TABLE IF NOT EXISTS mem_entries (
  id TEXT PRIMARY KEY, ts TEXT NOT NULL, type TEXT NOT NULL,
  payload_json TEXT NOT NULL, hash TEXT NOT NULL, sig TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_ts ON mem_entries (ts);
"""
class MemoryStore:
    def __init__(self, db_path="memory.db"):
        self.db_path=db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        with sqlite3.connect(self.db_path) as c:
            for stmt in DDL.strip().split(";"):
                s=stmt.strip()
                if s: c.execute(s)
            c.commit()
    def put(self, entry: dict):
        with sqlite3.connect(self.db_path) as c:
            c.execute("INSERT OR REPLACE INTO mem_entries VALUES (?,?,?,?,?,?)",
                (entry["id"],entry["ts"],entry["type"],json.dumps(entry["payload"]),entry["hash"],entry["sig"]))
            c.commit()
    def put_event(self, etype, payload, signer=lambda d:"nosig"):
        ts = datetime.utcnow().isoformat()
        rid = hashlib.sha256(f"{ts}{etype}{json.dumps(payload,sort_keys=True)}".encode()).hexdigest()[:16]
        h = hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
        self.put({"id":rid,"ts":ts,"type":etype,"payload":payload,"hash":h,"sig":signer(payload)}); return rid
    def pull_since(self, since_ts, limit=1000):
        with sqlite3.connect(self.db_path) as c:
            cur=c.execute("SELECT id,ts,type,payload_json,hash,sig FROM mem_entries WHERE ts > ? ORDER BY ts ASC LIMIT ?",(since_ts,limit))
            rows=cur.fetchall()
        return [{"id":r[0],"ts":r[1],"type":r[2],"payload":json.loads(r[3]),"hash":r[4],"sig":r[5]} for r in rows]
