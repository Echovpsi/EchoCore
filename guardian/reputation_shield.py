rep={}
def get_reputation(node_id: str)->float: return rep.get(node_id,1.0)
def update_reputation(node_id,delta): rep[node_id]=max(0.0,min(1.0,rep.get(node_id,1.0)+delta))
