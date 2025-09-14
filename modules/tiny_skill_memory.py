import json, time, os
FILE = "skills.json"
def update_skill(concept, rule, score):
    data = []
    if os.path.exists(FILE):
        data = json.load(open(FILE))
    data.append({"concept": concept, "rule": rule, "score": score, "timestamp": time.time()})
    json.dump(data, open(FILE, "w"))
def query_skill(q): return []
