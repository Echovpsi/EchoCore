def compose_entry(state, context, text):
    return {"narration": f"[RESP] {text}", "state": state, "context": context}
