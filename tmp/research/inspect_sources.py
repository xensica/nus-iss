from pathlib import Path
from html.parser import HTMLParser
import json,re
class Parser(HTMLParser):
    def __init__(self): super().__init__(); self.scripts=[]; self.links=[]; self.current=None
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='script': self.current=[a,'']
        if tag=='a' and 'whats-on' in a.get('href',''): self.links.append(a['href'])
    def handle_endtag(self,tag):
        if tag=='script' and self.current: self.scripts.append(self.current); self.current=None
    def handle_data(self,data):
        if self.current is not None: self.current[1]+=data
p=Parser();p.feed(Path('tmp/research/esplanade.txt').read_text(encoding='utf-8'))
print([(a,len(s),s[:80]) for a,s in p.scripts if len(s)>200])
print(list(dict.fromkeys(p.links))[:30])
for a,s in p.scripts:
    if a.get('id')=='__NEXT_DATA__':
        data=json.loads(s); Path('tmp/research/esplanade-data.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
        print('NEXT KEYS',data.keys())
print(Path('tmp/research/geocode.txt').read_text()[:1000])
