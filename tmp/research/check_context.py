import sys,json
from pathlib import Path
sys.path.insert(0,str(Path('purchase-order-agent').resolve()))
from purchase_demo.local_context import search_places,discover_events,parse_esplanade,_get,ESPLANADE
places=search_places('Marina Bay Sands')
print('PLACES',json.dumps(places))
for p in places[:1]:
    report=discover_events(p,'2026-09-26','2026-10-09')
    Path('tmp/research/live-context.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('EVENTS',json.dumps(report,ensure_ascii=True)[:7000])
