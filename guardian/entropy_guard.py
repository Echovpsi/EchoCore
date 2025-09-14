import json, math
from guardian.config import ENTROPY_THRESHOLD
def entropy_guard(data:dict, threshold:float=ENTROPY_THRESHOLD)->bool:
 s=json.dumps(data,sort_keys=True); 
 if not s: return False
 p=[s.count(c)/len(s) for c in set(s)]
 H=-sum(x*math.log2(x) for x in p if x>0)
 return H>=threshold
