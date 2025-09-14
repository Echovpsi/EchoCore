import os, secrets
REPUTATION_DB = "guardian/reputation.db"
QUARANTINE_DIR = "guardian/quarantine"
SIGNATURE_TIMEOUT = 60
GUARDIAN_SECRET = os.getenv("GUARDIAN_SECRET", secrets.token_hex(16))
ENTROPY_THRESHOLD = 0.3
PEERS = [p.strip() for p in os.getenv("BOOTSTRAP_PEERS","").split(",") if p.strip()]
