import hashlib, time, hmac, json
from guardian.config import GUARDIAN_SECRET, SIGNATURE_TIMEOUT
def sign_packet(data: dict) -> dict:
    ts = str(int(time.time()))
    body = json.dumps(data, sort_keys=True) + ts
    sig = hmac.new(GUARDIAN_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    return {"sig": sig, "ts": ts}
def verify_packet(packet: dict) -> bool:
    try:
        ts = int(packet.get("ts", 0))
        if abs(int(time.time()) - ts) > SIGNATURE_TIMEOUT: return False
        content = {k:v for k,v in packet.items() if k not in ("sig","ts")}
        body = json.dumps(content, sort_keys=True) + str(ts)
        exp = hmac.new(GUARDIAN_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(exp, packet.get("sig",""))
    except Exception: return False
