from pathlib import Path
import gzip,json,functools
@functools.lru_cache(maxsize=1)
def load_graph(path):
 with gzip.open(path,'rt',encoding='utf-8') as f:return json.load(f)
def lookup(path,uid):
 g=load_graph(str(path));result={'version':g['version'],'uid':uid,'P_T':g['P_T'].get(uid,[]),'T_S':g['T_S'].get(uid,[]),'P_E':[x for x in g['P_E'] if uid in [x['product_uid'],x['company_uid']]],'I_E':[x for x in g['I_E'] if uid in [x['investor_uid'],x['company_uid']]],'T_S_threshold':g['T_S_threshold'],'ignored_institution_names':g['ignored_institution_names']}
 return result
