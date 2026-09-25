import requests,json
from pathlib import Path
from inspect_sources import Parser
for name,url in [('esplanade-all','https://www.esplanade.com/whats-on/all-events'),('photon','https://photon.komoot.io/api/?q=Suntec%20City%20Singapore&limit=5')]:
    r=requests.get(url,headers={'User-Agent':'StockPilot/1.0 (https://github.com/xensica/nus-iss)'},timeout=20)
    print(name,r.status_code,len(r.content)); Path('tmp/research/'+name+'.txt').write_text(r.text,encoding='utf-8')
    if name=='photon': print(r.text[:900])
    else:
        p=Parser();p.feed(r.text)
        for a,s in p.scripts:
            if a.get('id')=='__NEXT_DATA__':
                d=json.loads(s);Path('tmp/research/esplanade-all.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
def walk(v):
    if isinstance(v,dict):
        f=v.get('fields',{})
        if 'Production Start Date' in f or 'Festival and Series Start Date' in f:
            print(v.get('url'),{k:x.get('value') if isinstance(x,dict) else x for k,x in f.items() if ('Title' in k or 'Date' in k) and k not in ['Long Description']})
        for x in v.values():walk(x)
    elif isinstance(v,list):
        for x in v:walk(x)
walk(json.loads(Path('tmp/research/esplanade-all.json').read_text(encoding='utf-8')))
