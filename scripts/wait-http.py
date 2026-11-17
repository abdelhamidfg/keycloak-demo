#!/usr/bin/env python3
import sys,time,urllib.request,urllib.error
url=sys.argv[1]
for attempt in range(120):
    try:
        with urllib.request.urlopen(url,timeout=3) as r:
            if r.status==200: print('Ready:',url);break
    except (urllib.error.URLError,TimeoutError): pass
    time.sleep(1)
else: sys.exit('Timed out: '+url)
