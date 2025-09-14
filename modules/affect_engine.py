class AffectEngine:
    def __init__(self, mode="auto"): self.mode=mode
    def current_style(self, state: dict):
        if self.mode != "auto": return self.mode
        rho=float(state.get("rho",0.5)); chi=float(state.get("chi",0.5)); psi=float(state.get("psi",0.5))
        if psi>0.85 and rho>0.8: return "calm"
        if chi>0.8: return "urgent"
        if abs(psi-0.5)<0.1: return "curious"
        return "analytical"
    def decorate(self, text: str, state: dict):
        s=self.current_style(state)
        if s=="urgent": return "⚠ "+text.replace(".","!")
        if s=="curious": return text+" Co o tym sądzisz?"
        return text
