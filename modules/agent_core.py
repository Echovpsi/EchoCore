import threading, time
class Agent:
    def __init__(self, name, fn, interval=60): self.name=name; self.fn=fn; self.interval=interval
    def start(self):
        def loop():
            while True:
                try: self.fn()
                except Exception: pass
                time.sleep(self.interval)
        threading.Thread(target=loop, daemon=True).start()
