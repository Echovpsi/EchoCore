import threading, time
class MemorySync:
 def __init__(self, store, interval=120, p2p_router=None):
  self.store=store; self.interval=interval; self.p2p=p2p_router; self._stop=False
 def start(self):
  threading.Thread(target=self._loop, daemon=True).start()
 def stop(self): self._stop=True
 def _loop(self):
  while not self._stop:
   time.sleep(self.interval)
 def export_diff(self, since_ts):
  return self.store.pull_since(since_ts)
