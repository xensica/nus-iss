"""User-triggered Singapore place lookup and limited, source-linked event discovery.

Public venue listings are context, never attendance data or a learned demand model.
No network calls happen during import or ordinary recalculation.
"""
import json
import math
import os
import threading
import time
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from dotenv import load_dotenv

SGT=timezone(timedelta(hours=8))
HEADERS={'User-Agent':'StockPilot/2.0 (https://github.com/xensica/nus-iss)'}
ESPLANADE='https://www.esplanade.com'
ESPLANADE_POINT=(1.2898,103.8558)  # approximate arts-centre location, not a storefront
_cache={}
_lock=threading.Lock()
_last_lookup=0.0


def distance_km(lat1,lon1,lat2,lon2):
    values=[float(x) for x in (lat1,lon1,lat2,lon2)]
    if not all(math.isfinite(x) for x in values) or not (-90<=values[0]<=90 and -90<=values[2]<=90 and -180<=values[1]<=180 and -180<=values[3]<=180):
        raise ValueError('Invalid map coordinates.')
    a,b,c,d=map(math.radians,values)
    h=math.sin((c-a)/2)**2+math.cos(a)*math.cos(c)*math.sin((d-b)/2)**2
    return 6371*2*math.asin(min(1,math.sqrt(h)))


def _get(url,params=None,get=None):
    """Bound response size and duration; no user-provided event URLs are fetched."""
    response=(get or requests.get)(url,params=params,headers=HEADERS,timeout=(5,15))
    response.raise_for_status()
    if len(response.content)>3_000_000: raise ValueError('Source response too large.')
    return response


def search_places(query,get=None):
    load_dotenv(Path(__file__).with_name('.env'))
    query=' '.join(query.strip().split())
    if not 3<=len(query)<=180: raise ValueError('Enter a mall, public address or postal code (3-180 characters).')
    endpoint=os.getenv('STOCKPILOT_GEOCODER_URL','https://photon.komoot.io/api/')
    if not endpoint.startswith('https://'): raise ValueError('The geocoder must use HTTPS.')
    key=('place',endpoint,query.casefold())
    # Serialize requests across this process and cache results; no keystroke autocomplete.
    global _last_lookup
    with _lock:
        if not get and key in _cache and time.time()-_cache[key][0]<86400:
            return deepcopy(_cache[key][1])
        if not get: time.sleep(max(0,1.1-(time.monotonic()-_last_lookup)))
        try:
            _last_lookup=time.monotonic()
            data=_get(endpoint,dict(q=query if 'singapore' in query.lower() else query+', Singapore',limit=6,lang='en',lat=1.35,lon=103.82),get).json()
            results=[]; seen=set()
            for feature in data.get('features',[]):
                props=feature.get('properties',{}); lon,lat=feature['geometry']['coordinates'][:2]
                if props.get('countrycode','').upper()!='SG' or not (1.1<=lat<=1.5 and 103.5<=lon<=104.2): continue
                if props.get('osm_key')=='highway': continue
                label=', '.join(dict.fromkeys(str(props[k]) for k in ['name','housenumber','street','district','postcode'] if props.get(k)))
                identity=(label,round(lat,4),round(lon,4))
                if identity in seen: continue
                seen.add(identity); results.append(dict(label=label,lat=lat,lon=lon,source='Photon / OpenStreetMap'))
            if not get:
                if len(_cache)>=256:_cache.pop(next(iter(_cache)))
                _cache[key]=(time.time(),results)
            return deepcopy(results)
        except (requests.RequestException,ValueError,KeyError,TypeError):
            raise ValueError('Address search is temporarily unavailable. Try again later or enter map coordinates in Store settings.') from None


class _PageData(HTMLParser):
    def __init__(self): super().__init__(); self.capture=False; self.chunks=[]
    def handle_starttag(self,tag,attrs):
        if tag=='script': self.capture=dict(attrs).get('id')=='__NEXT_DATA__'
    def handle_endtag(self,tag):
        if tag=='script': self.capture=False
    def handle_data(self,data):
        if self.capture:self.chunks.append(data)


def _walk(value):
    if isinstance(value,dict):
        yield value
        for child in value.values(): yield from _walk(child)
    elif isinstance(value,list):
        for child in value: yield from _walk(child)


def _day(value):
    parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    return (parsed.astimezone(SGT) if parsed.tzinfo else parsed).date()


def parse_esplanade(html):
    parser=_PageData();parser.feed(html)
    if not parser.chunks: raise ValueError('Event listing format changed.')
    data=json.loads(''.join(parser.chunks)); events={}; festivals={}
    for node in _walk(data):
        # Public programme cards use a compact schema instead of Sitecore fields.
        path=node.get('url','')
        if node.get('startDate') and node.get('title') and isinstance(path,str) and path.startswith('/whats-on/'):
            try:
                name=unescape(node['title']).strip()
                # School programmes and online listings cannot be placed at this venue.
                if not node.get('venueTagKeys') or any(word in name.lower() for word in ['schools only','online']):continue
                start=_day(node['startDate']);end=_day(node.get('endDate') or node['startDate'])
                if end<start:continue
                url=urljoin(ESPLANADE,path)
                events[url]=dict(id=url,title=name[:200],start=start.isoformat(),end=end.isoformat(),url=url,
                    venue='Esplanade area (approx.)',lat=ESPLANADE_POINT[0],lon=ESPLANADE_POINT[1],
                    source='Esplanade official programme listing',date_note='Published programme date range. Confirm the exact venue and individual showtimes in the source before applying.')
            except (ValueError,TypeError):pass
        fields=node.get('fields',{})
        if not isinstance(fields,dict): continue
        def val(key):
            item=fields.get(key,{})
            return item.get('value','') if isinstance(item,dict) else ''
        path=node.get('url','')
        if not isinstance(path,str) or not path.startswith('/whats-on/'):continue
        try:
            if val('Production Start Date'):
                start=_day(val('Production Start Date'));end=_day(val('Production End Date') or val('Production Start Date'))
                nature=json.dumps(fields.get('Production Performance Nature',[]))
                if 'Onsite' not in nature and 'At Esplanade' not in nature: continue
                name=unescape(val('Page Title') or node.get('displayName','')).strip()
                if not name or end<start:continue
                url=urljoin(ESPLANADE,path)
                events[url]=dict(id=url,title=name[:200],start=start.isoformat(),end=end.isoformat(),url=url,
                    venue='Esplanade',lat=ESPLANADE_POINT[0],lon=ESPLANADE_POINT[1],
                    source='Esplanade official listing',date_note='Listed production date range; check the source for individual showtimes.')
            elif val('Festival and Series Start Date') and val('Festival and Series End Date'):
                festivals[path]=dict(path=path,start=_day(val('Festival and Series Start Date')).isoformat(),end=_day(val('Festival and Series End Date')).isoformat())
        except (ValueError,TypeError):continue
    return list(events.values()),list(festivals.values())


def discover_events(location,start,end,radius=2.0,get=None):
    start=date.fromisoformat(str(start));end=date.fromisoformat(str(end))
    if end<start or (end-start).days>31 or not .1<=float(radius)<=10: raise ValueError('Use a window up to 31 days and radius up to 10 km.')
    lat,lon=float(location['lat']),float(location['lon'])
    distance=distance_km(lat,lon,*ESPLANADE_POINT)
    base=dict(events=[],checked_at=datetime.now(SGT).isoformat(),start=start.isoformat(),end=end.isoformat(),radius=radius,
        location=dict(location),coverage='Esplanade published listings only. Other malls, venues and unlisted events are not covered.',status='ok')
    if distance>radius:
        return dict(base,status='outside_coverage',message='Your radius does not include the connected Esplanade venue. This does not mean there are no nearby events.')
    key=('events',start.isoformat(),end.isoformat())
    with _lock:
        cached=_cache.get(key)
    if not get and cached and time.time()-cached[0]<1800:
        events,checked_at=cached[1]
        return dict(base,events=[dict(e,distance_km=distance) for e in events],checked_at=checked_at,cached=True)
    events={}; failures=0
    try:
        rows,festivals=parse_esplanade(_get(ESPLANADE+'/whats-on',get=get).text)
        events.update({e['id']:e for e in rows})
        relevant=[f for f in festivals if f['start']<=end.isoformat() and f['end']>=start.isoformat()][:3]
        for festival in relevant:
            url=urljoin(ESPLANADE,festival['path'])
            if urlparse(url).netloc!='www.esplanade.com':continue
            try:
                rows,_=parse_esplanade(_get(url,get=get).text)
                events.update({e['id']:e for e in rows})
            except (requests.RequestException,ValueError,TypeError): failures+=1
        filtered=sorted((e for e in events.values() if e['start']<=end.isoformat() and e['end']>=start.isoformat()),key=lambda e:(e['start'],e['title']))
        # An empty parser result could be a changed site, not evidence of no events.
        if not events and not festivals: raise ValueError('No readable event records.')
        result=dict(base,events=[dict(e,distance_km=distance) for e in filtered],status='partial' if failures else 'ok')
        if not failures and not get:
            with _lock: _cache[key]=(time.time(),(filtered,result['checked_at']))
        return result
    except (requests.RequestException,ValueError,KeyError,TypeError):
        return dict(base,status='unavailable',message='The event source could not be checked. Your purchasing plan is unchanged. Retry later or use a known event in Store settings.')


def scenario_overrides(event,as_of,product_ids,uplift,existing=None):
    """Explicit human what-if, with cited evidence retained in the saved draft."""
    if not product_ids:raise ValueError('Choose at least one product.')
    if not 0<=uplift<=100:raise ValueError('Choose an uplift from 0 to 100%.')
    as_of=date.fromisoformat(str(as_of)); first=max(date.fromisoformat(event['start']),as_of+timedelta(days=1)); last=min(date.fromisoformat(event['end']),as_of+timedelta(days=14))
    if first>last:raise ValueError('This event is outside your stock-planning dates. Check the inventory snapshot date first.')
    overrides=deepcopy(existing or {})
    for pid in product_ids:
        overrides[pid]=dict(overrides.get(pid,{}),scenario='Nearby event scenario',event_start=(first-as_of).days,
            event_duration=(last-first).days+1,uplift=uplift,
            event_evidence=dict(title=event['title'],url=event['url'],start=event['start'],end=event['end'],
                distance_km=event.get('distance_km'),source=event['source'],assumption='Owner-selected demand uplift; not measured footfall or a learned effect.'))
    return overrides
