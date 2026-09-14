"""Live retrieval from an explicit official-source catalogue; no invented rules."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
import re
import time
import urllib.request

CATALOG = (
 {'id':'sa-residential','url':'https://momah.gov.sa/ar/node/15715','title':'اشتراطات إنشاء المباني السكنية — وزارة البلديات والإسكان','kind':'official_reference','jurisdiction':'Saudi Arabia',
  'use':'مرجع الاشتراطات السكنية العام. يلزم التحقق من اشتراطات قطعة الأرض والمدينة قبل تطبيق أي رقم.'},
 {'id':'apartment-design','url':'https://www.planning.nsw.gov.au/the-planning-system/housing/apartment-design-guide','title':'دليل تصميم الشقق — حكومة نيو ساوث ويلز','kind':'design_guidance','jurisdiction':'New South Wales, Australia',
  'use':'استرشاد في تنظيم الشقق وتقييم بدائل التصميم. ليس اشتراطًا سعوديًا ولا إثباتًا لملاءمة قطعة الأرض.'},
)
_CACHE = {}
class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.skip=0; self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'): self.skip+=1
    def handle_endtag(self,tag):
        if tag in ('script','style'): self.skip=max(0,self.skip-1)
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)

def _fetch(source):
    checked=datetime.now(timezone.utc).isoformat()
    try:
        # Redirects are disabled: user data never controls a destination.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*args,**kwargs): return None
        opener=urllib.request.build_opener(NoRedirect)
        with opener.open(urllib.request.Request(source['url'],headers={'User-Agent':'ACS-reference-reader/1.0'}),timeout=8) as response:
            raw=response.read(1_000_001)
            if len(raw)>1_000_000: raise ValueError('too large')
        page=Page();page.feed(raw.decode('utf-8',errors='replace'))
        text=re.sub(r'\s+',' ',' '.join(page.parts)).strip()
        marker='اشتراطات إنشاء المباني السكنية' if source['id']=='sa-residential' else 'Apartment Design Guide'
        if marker.casefold() not in text.casefold():raise ValueError('unverified document')
        return dict(source,status='retrieved',checked_at=checked,information_used=source['use'])
    except Exception:
        return dict(source,status='unavailable',checked_at=checked,information_used=None)

def research(city='',building_type='residential'):
    if not isinstance(city,str) or len(city)>120 or building_type not in {'residential','warehouse'}:raise ValueError('Invalid research context')
    key=building_type; cached=_CACHE.get(key)
    if cached and time.monotonic()-cached[0]<3600:sources=cached[1]
    else:
        with ThreadPoolExecutor(max_workers=2) as pool:
            sources=list(pool.map(_fetch,CATALOG if building_type=='residential' else ()))
        _CACHE[key]=(time.monotonic(),sources)
    return {'ok':True,'city':city.strip(),'sources':sources,'search_scope':'official_source_catalogue',
      'local_rules_status':'NOT_VERIFIED','numeric_rules_applied':False,
      'message':'تمت مراجعة المراجع الرسمية المتاحة. اشتراطات المدينة وقطعة الأرض لم تتحقق بعد.' if any(s['status']=='retrieved' for s in sources) else 'تعذّر جلب المراجع الآن. لم تُستخدم اشتراطات أو مراجع غير متحققة.'}
