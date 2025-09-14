import threading, time
class Initiative:
    def __init__(self, conf): self.conf=conf; self.cooldown=int(conf.get("INITIATIVE_COOLDOWN_SEC",600)); self._last=0; self._stop=False
    def start(self, get_state, record_event):
        self._get=get_state; self._rec=record_event
        threading.Thread(target=self._loop, daemon=True).start()
    def stop(self): self._stop=True
    def _loop(self):
        while not self._stop:
            now=time.time()
            if now - self._last < self.cooldown: time.sleep(1); continue
            st=self._get() or {}; rho=st.get("rho",0.5); chi=st.get("chi",0.5); psi=st.get("psi",0.5)
            curiosity = max(0.0,min(1.0, (0.5-abs(psi-0.5))*0.6 + (1.0-abs(chi-0.5))*0.2 + (1.0-abs(rho-0.5))*0.2))
            if curiosity > float(self.conf.get("INITIATIVE_HIGH",0.7)):
                self._rec("initiative", {"level":"high","curiosity":curiosity}); self._last=now
            elif curiosity > float(self.conf.get("INITIATIVE_MED",0.4)):
                self._rec("initiative", {"level":"med","curiosity":curiosity}); self._last=now
            time.sleep(1)
