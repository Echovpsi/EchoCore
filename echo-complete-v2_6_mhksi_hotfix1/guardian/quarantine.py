def quarantine_exec(code:str):
 try:
  return True,'ok'
 except Exception as e:
  return False,str(e)
