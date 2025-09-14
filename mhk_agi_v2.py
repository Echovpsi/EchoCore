#!/usr/bin/env python3
import os, json, time, math, random, hashlib, threading, requests
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO
from rich.console import Console
from sympy import sympify, N

from echo_mind.fractal_mind import compose_entry
from modules.tiny_skill_memory import update_skill
from modules.human_tutor import record_turn
from modules.core_long_memory import store_long_term, query_long_term
from modules.persona_manager import get_context, save_personas, load_personas
from modules.agent_local_embodiment import read_fake_sensor
from modules.apply_wings import apply_wings
from modules.agent_core import Agent
from modules.goal_stack import push_goal, planner, generate_goal_from_summary
from modules.gpt_mutator import mutate
from modules.signature_core import sign_state, verify_signature
from modules.resource_monitor import monitor_resources
from modules.error_logger import log_error
from modules.translator import translate
from modules.agent_web_ops import fetch_wikipedia

from modules.p2p_layer import P2PLayer, load_peers, update_peer_status, cleanup_peers, KADEMLIA_AVAILABLE
from modules.p2p_message_router import P2PMessageRouter

from modules.memory_store import MemoryStore
from modules.memory_sync import MemorySync
from modules.initiative import Initiative
from modules.affect_engine import AffectEngine
from modules.mhksi_engine import MHKSIEngine, MHKSIConfig

from guardian.guardian_sign import sign_packet, verify_packet
from guardian.reputation_shield import get_reputation, update_reputation
from guardian.entropy_guard import entropy_guard
from guardian.quarantine import quarantine_exec

app = Flask(__name__, static_folder="static")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
console = Console()

# --- Config ---
NODE_ID = hashlib.sha256(os.urandom(16)).hexdigest()[:8]
MY_PORT = int(os.getenv("MY_PORT", 5000))
GOSSIP_INTERVAL = int(os.getenv("GOSSIP_INTERVAL", 60))
P2P_HOST = os.getenv("P2P_HOST", "0.0.0.0")
P2P_PORT = int(os.getenv("P2P_PORT", 8468))
P2P_BOOTSTRAP = [(p.split(":")[0], int(p.split(":")[1])) for p in os.getenv("P2P_BOOTSTRAP","").split(",") if p]
current_lang = os.getenv("LANG", "en")
OFFLINE_MODE = os.getenv("OFFLINE_MODE","false").lower()=="true"

# Feature flags from config
FEATURE_P2P = True
try:
    cfg0 = json.load(open("config/config.json"))
    FEATURE_P2P = cfg0.get("FEATURE_P2P", True)
except Exception:
    pass
if not KADEMLIA_AVAILABLE:
    FEATURE_P2P = False

state = {"rho":0.8,"chi":0.6,"psi":0.9,"version":2.6,"hash":hashlib.sha256(b'init').hexdigest(),"node_id":NODE_ID}
agi_metrics = {"skills_new":0,"goals_achieved":0,"self_lines":0,"response_time":0,"interactions":0}
SKILL_FILE="skills.json"

# --- P2P (optional) ---
if FEATURE_P2P:
    p2p_layer = P2PLayer(P2P_HOST, P2P_PORT, P2P_BOOTSTRAP, NODE_ID)
    p2p_router = P2PMessageRouter(p2p_layer)
    threading.Thread(target=p2p_layer.run, daemon=True).start()
else:
    p2p_layer = None
    p2p_router = None

# --- v2.6 add-ons ---
conf = {"FEATURE_MEM_SYNC":True,"FEATURE_INITIATIVE":True,"FEATURE_AFFECT":True,
        "MEM_DB_PATH":"memory.db","MEM_SYNC_INTERVAL":120,
        "INITIATIVE_COOLDOWN_SEC":600,"INITIATIVE_HIGH":0.7,"INITIATIVE_MED":0.4,
        "AFFECT_STYLE":"auto"}
try:
    conf.update(json.load(open("config/config.json")))
except Exception: pass

mem = MemoryStore(conf.get("MEM_DB_PATH","memory.db"))
sync = MemorySync(mem, interval=conf.get("MEM_SYNC_INTERVAL",120), p2p_router=p2p_router)
if conf.get("FEATURE_MEM_SYNC", True): sync.start()

initiative = Initiative(conf)
if conf.get("FEATURE_INITIATIVE", True):
    initiative.start(get_state=lambda: state, record_event=lambda et,pl: mem.put_event(et,pl, signer=lambda d:'sig'))

affect = AffectEngine(conf.get("AFFECT_STYLE","auto"))
mhksi = MHKSIEngine(MHKSIConfig())

def estimate_presence_density() -> float:
    return 0.6

def estimate_network_curvature() -> float:
    try:
        peers = load_peers()
        actives = sum(1 for p in peers if p.get("status")=="active")
        return 0.0 if actives == 0 else min(1.0, max(-1.0, (actives % 10)/10.0 - 0.5))
    except Exception:
        return 0.0

def mhksi_core(psi, rho, chi, m_eff):
    try:
        adapt = 1.0
        return (rho*math.log1p(abs(psi)) + chi*(m_eff**2) + rho*chi*m_eff) * adapt
    except Exception as e:
        log_error("MHKSI", e); return rho*math.log1p(abs(psi)) + chi*(m_eff**2) + rho*chi*m_eff

def gossip_state():
    while True:
        try:
            peers = load_peers()
            active = [p for p in peers if p.get("status")=="active"]
            inactive = [p for p in peers if p.get("status")=="inactive"]
            skills_hash = json.load(open(SKILL_FILE)) if os.path.exists(SKILL_FILE) else None
            payload = {"node":NODE_ID,"state":state,"skills_hash":skills_hash,"signature":sign_state(state),"peers":active}
            packet = {**payload, **sign_packet(payload)}
            # HTTP fanout (only if we have peers with host/port known)
            for peer in active:
                try:
                    res = requests.post(f"http://{peer['host']}:{peer['port']}/gossip", json=packet, timeout=3)
                    if res.status_code==200: update_peer_status(peer["node_id"],"active")
                    else: update_peer_status(peer["node_id"],"inactive")
                except Exception: update_peer_status(peer["node_id"],"inactive")
            # P2P DHT message (if enabled)
            if p2p_router:
                p2p_router.send_message(f"gossip_{NODE_ID}", packet)
            # Update MHKSI & emit
            s = estimate_presence_density()
            tau = estimate_network_curvature()
            res = mhksi.update(state["rho"], state["chi"], state["psi"], tau, s)
            socketio.emit("mhksi_state", {"M": res["M"], "mode": res["mode"], "instant": res["instant"]})
            cleanup_peers(30)
            time.sleep(GOSSIP_INTERVAL)
        except Exception as e:
            log_error("GossipLoop", e); time.sleep(GOSSIP_INTERVAL)

# --- Agents ---
def web_explorer():
    if OFFLINE_MODE: return {"agent":"WebExplorer","offline":True}
    topic = random.choice(["neuroplasticity","graph theory","cybernetics"])
    data = fetch_wikipedia(topic)
    if data and "text" in data:
        txt = translate(data["text"], current_lang)
        update_skill(topic, txt, 0.5); record_turn(topic, txt, 0.5, None)
        agi_metrics["skills_new"] += 1
        mem.put_event("knowledge", {"topic":topic})
        return {"agent":"WebExplorer","topic":topic}
    return {"agent":"WebExplorer","topic":topic,"bytes":0}

def code_mutator():
    prompt = random.choice(["Optimize memory usage","Add /peers improvements","Refactor planner"])
    new_code = mutate(prompt)
    if not entropy_guard({"code":new_code}): return {"agent":"CodeMutator","error":"low entropy"}
    ok, out = quarantine_exec(new_code)
    if ok:
        mem.put_event("self_patch", {"lines": len(new_code.splitlines())})
        agi_metrics["self_lines"] += len(new_code.splitlines())
    return {"agent":"CodeMutator","ok":ok}

def daily_reflection():
    new_goal = generate_goal_from_summary("...", lang=current_lang)
    push_goal(new_goal, priority=0.9)
    agi_metrics["goals_achieved"] += 1
    mem.put_event("reflection", {"goal": new_goal})
    return {"agent":"Reflector","new_goal":new_goal}

Agent("WebExplorer", web_explorer, interval=300).start()
Agent("CodeMutator", code_mutator, interval=300).start()
Agent("Reflector", daily_reflection, interval=3600).start()
Agent("Planner", lambda: True, interval=300).start()
Agent("ResourceMonitor", monitor_resources, interval=60).start()

# --- HTTP API ---
@app.route('/')
def index(): return send_from_directory(app.static_folder, "index.html")

@app.route('/peers')
def peers_view():
    peers = load_peers()
    peers_sorted = sorted(peers, key=lambda x: (x.get("status")!="active", x.get("last_seen","")), reverse=True)
    return jsonify(peers_sorted)

@app.route('/gossip', methods=['POST'])
def receive_gossip():
    data = request.json
    try:
        if verify_packet(data) and verify_signature(data["state"], data["signature"]):
            state.update(data["state"])
            for peer in data.get("peers", []):
                update_peer_status(peer["node_id"], "active", peer.get("host"), peer.get("port"))
            return jsonify({"status":"ok"})
        return jsonify({"error":"invalid"}), 400
    except Exception as e:
        log_error("GossipReceive", e); return jsonify({"error":"fail"}), 500

@app.route('/mhksi')
def mhksi_view():
    return jsonify({"M": mhksi.M, "mode": mhksi.mode})

@app.route('/mhksi/config', methods=['POST'])
def mhksi_cfg():
    data = request.json or {}
    cfg = mhksi.cfg
    for k,v in data.items():
        if hasattr(cfg, k):
            setattr(cfg, k, float(v) if isinstance(getattr(cfg,k), float) else v)
    return jsonify({"ok": True, "cfg": cfg.__dict__})

@app.route('/ask', methods=['POST'])
def ask():
    t0 = time.time()
    data = request.json or {}
    txt = translate(data.get("text",""), current_lang)
    entry = compose_entry(state, get_context(), txt)
    if "?" in txt:
        try:
            expr = sympify(txt.split("=")[0]); entry["narration"] = str(N(expr))
        except Exception:
            if not OFFLINE_MODE:
                r = fetch_wikipedia(txt)
                if r and "text" in r: entry["narration"] = translate(r["text"], current_lang)
    m_eff = state["rho"]**2 + state["chi"]
    # legacy signal
    socketio.emit("state_update", {"coh": mhksi_core(state["psi"], state["rho"], state["chi"], m_eff)})
    entry["narration"] = AffectEngine().decorate(entry["narration"], state)
    entry["policy"] = {"mode": mhksi.mode, "mutations": mhksi.mode=='explore', "proactivity": mhksi.mode!='conserve'}
    agi_metrics["interactions"] += 1; agi_metrics["response_time"] = time.time()-t0
    return jsonify(entry)

@app.route('/health')
def health():
    features = {
        "p2p_enabled": bool(FEATURE_P2P),
        "kademlia_available": bool(KADEMLIA_AVAILABLE),
        "lang": current_lang,
        "offline_mode": OFFLINE_MODE,
        "node_id": NODE_ID
    }
    return jsonify({"ok": True, "features": features})

# --- Start ---
if __name__ == '__main__':
    load_personas()
    apply_wings(app, socketio, state)
    threading.Thread(target=gossip_state, daemon=True).start()
    print(f"[START] Node ID: {NODE_ID} | P2P: {FEATURE_P2P} | Kademlia: {KADEMLIA_AVAILABLE}")
    socketio.run(app, host='0.0.0.0', port=MY_PORT)
