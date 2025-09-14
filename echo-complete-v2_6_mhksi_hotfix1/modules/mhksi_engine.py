import math, time
from dataclasses import dataclass

def _sigmoid(x: float) -> float:
    x = max(-20.0, min(20.0, x))
    return 1.0 / (1.0 + math.exp(-x))

@dataclass
class MHKSIConfig:
    a1: float = 1.0
    a2: float = 1.0
    a3: float = 1.0
    a4: float = 0.7
    a5: float = 0.6
    ema_alpha: float = 0.12
    eps: float = 1e-6
    m0: float = 1.0
    on_threshold: float = 0.72
    off_threshold: float = 0.28

class MHKSIEngine:
    def __init__(self, cfg: MHKSIConfig = MHKSIConfig()):
        self.cfg = cfg
        self.M = 0.5
        self.mode = "steady"
        self.last_update = time.time()

    def _meff(self, s: float) -> float:
        return self.cfg.m0 * (1.0 + math.log(max(self.cfg.eps, s) + self.cfg.eps))

    def compute_instant(self, rho: float, chi: float, psi: float, tau: float, s: float) -> float:
        rho = max(0, min(1, rho)); chi = max(0, min(1, chi)); psi = max(0, min(1, psi))
        tau = max(-1, min(1, tau)); s = max(0, min(1, s))
        meff = self._meff(s)
        z = (self.cfg.a1 * math.log(1.0 + self.cfg.eps + psi)
             + self.cfg.a2 * (1.0 - chi)
             + self.cfg.a3 * rho
             + self.cfg.a4 * tau
             - self.cfg.a5 * meff)
        return _sigmoid(z)

    def update(self, rho: float, chi: float, psi: float, tau: float, s: float) -> dict:
        inst = self.compute_instant(rho, chi, psi, tau, s)
        self.M = (1.0 - self.cfg.ema_alpha) * self.M + self.cfg.ema_alpha * inst
        if self.M >= self.cfg.on_threshold and self.mode != "explore":
            self.mode = "explore"
        elif self.M <= self.cfg.off_threshold and self.mode != "conserve":
            self.mode = "conserve"
        elif self.cfg.off_threshold < self.M < self.cfg.on_threshold:
            self.mode = "steady"
        self.last_update = time.time()
        return {"M": self.M, "instant": inst, "mode": self.mode}
