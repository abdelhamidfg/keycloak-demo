#!/usr/bin/env python3
"""Create the isolated demo realm on an existing Keycloak; never overwrite another realm."""
import argparse,json,os,sys,urllib.request,urllib.parse,urllib.error
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--keycloak-url',required=True)
p.add_argument('--manifest',required=True)
a=p.parse_args()
base=a.keycloak_url.rstrip('/')
user=os.environ.get('KC_ADMIN_USER')
password=os.environ.get('KC_ADMIN_PASSWORD')
if not user or not password:sys.exit('Set KC_ADMIN_USER and KC_ADMIN_PASSWORD for the existing Keycloak administrator.')
manifest=json.loads(Path(a.manifest).read_text())
realm=json.loads(next(x for x in manifest['items'] if x['kind']=='Secret' and x['metadata']['name']=='keycloak-realm')['stringData']['realm.json'])
form=urllib.parse.urlencode({'client_id':'admin-cli','grant_type':'password','username':user,'password':password}).encode()
try:
    with urllib.request.urlopen(base+'/realms/master/protocol/openid-connect/token',form,timeout=30) as r:token=json.load(r)['access_token']
except urllib.error.HTTPError as e:sys.exit(f'Administrator login failed (HTTP {e.code}). No realm was changed.')
headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'}
url=base+'/admin/realms/'+urllib.parse.quote(realm['realm'],safe='')
try:
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=30):pass
except urllib.error.HTTPError as e:
    if e.code!=404:sys.exit(f'Cannot check realm existence (HTTP {e.code}). No realm was changed.')
else:sys.exit(f'Realm {realm["realm"]} already exists; refusing to overwrite it. Review/update it explicitly.')
with urllib.request.urlopen(urllib.request.Request(base+'/admin/realms',headers=headers,data=json.dumps(realm).encode(),method='POST'),timeout=60) as r:
    if r.status!=201:sys.exit(f'Unexpected import status: {r.status}')
print(f'Created realm {realm["realm"]} on {base}. Existing realms were not modified.')
