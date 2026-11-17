#!/usr/bin/env python3
"""Real Keycloak integration test: code + PKCE login, then API permission checks.
Runs against the supplied demo login theme, without enabling password grants.
Resets are intentionally external: restart Order API before each full test run.
"""
import base64, hashlib, html.parser, http.cookiejar, json, os, secrets
import urllib.error, urllib.parse, urllib.request

KC=os.environ.get('KEYCLOAK_URL','http://localhost:8080')
CUSTOMERS=os.environ.get('CUSTOMER_URL','http://localhost:8081')
ORDERS=os.environ.get('ORDER_URL','http://localhost:8082')
REDIRECT='http://127.0.0.1:8765/callback'
class LoginForm(html.parser.HTMLParser):
    action=None
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='form' and attrs.get('id')=='kc-form-login': self.action=attrs['action']
class NoCallback(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if newurl.startswith(REDIRECT):return None
        return super().redirect_request(req,fp,code,msg,headers,newurl)
def login(user,password,wrong_verifier=False):
    verifier=secrets.token_urlsafe(48)
    challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    state=secrets.token_urlsafe(24)
    jar=http.cookiejar.CookieJar()
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar),NoCallback())
    query=urllib.parse.urlencode({'client_id':'commerce-postman','redirect_uri':REDIRECT,'response_type':'code','scope':'openid profile email','state':state,'code_challenge':challenge,'code_challenge_method':'S256'})
    form=LoginForm()
    with opener.open(KC+'/realms/commerce-demo/protocol/openid-connect/auth?'+query,timeout=30) as r:form.feed(r.read().decode())
    assert form.action, 'Keycloak login form was not found'
    # Browsers treat localhost as trustworthy; urllib otherwise drops Secure cookies over HTTP.
    if urllib.parse.urlparse(KC).scheme == 'http' and urllib.parse.urlparse(KC).hostname in ('localhost', '127.0.0.1'):
        for cookie in jar: cookie.secure=False
    try:
        with opener.open(form.action,urllib.parse.urlencode({'username':user,'password':password,'credentialId':''}).encode(),timeout=30) as r:
            raise AssertionError('Login did not redirect; check credentials and required actions')
    except urllib.error.HTTPError as e:
        assert e.code==302, f'Unexpected login response {e.code}'
        result=urllib.parse.parse_qs(urllib.parse.urlparse(e.headers['Location']).query)
    assert result.get('state')==[state], 'OIDC state mismatch'
    data=urllib.parse.urlencode({'grant_type':'authorization_code','client_id':'commerce-postman','redirect_uri':REDIRECT,'code':result['code'][0],'code_verifier':secrets.token_urlsafe(48) if wrong_verifier else verifier}).encode()
    try:
        with opener.open(KC+'/realms/commerce-demo/protocol/openid-connect/token',data,timeout=30) as r:
            tokens=json.load(r)
    except urllib.error.HTTPError as e:
        if wrong_verifier and e.code==400:
            print('PASS Incorrect PKCE verifier rejected (400)'); return None
        raise
    assert not wrong_verifier, 'Incorrect PKCE verifier unexpectedly accepted'
    return tokens

def call(name,url,status,token=None,method='GET',body=None,headers=None):
    h=dict(headers or {})
    if token:h['Authorization']='Bearer '+token
    if body is not None:h['Content-Type']='application/json'
    req=urllib.request.Request(url,data=json.dumps(body).encode() if body is not None else None,headers=h,method=method)
    try:response=urllib.request.urlopen(req,timeout=30)
    except urllib.error.HTTPError as e:response=e
    with response:
        actual=response.code;raw=response.read().decode();rh=response.headers
    assert actual==status,f'{name}: expected {status}, got {actual}: {raw[:300]}'
    print(f'PASS {name} ({actual})')
    return (json.loads(raw) if raw and raw.startswith(('{','[')) else raw),rh

def main():
    alice_password=os.environ.get('ALICE_PASSWORD','alice-demo-password')
    bob_password=os.environ.get('BOB_PASSWORD','bob-demo-password')
    login('alice',alice_password,wrong_verifier=True)
    alice=login('alice',alice_password);bob=login('bob',bob_password)
    call('Anonymous customer inquiry',CUSTOMERS+'/api/customers',401)
    call('Anonymous order inquiry',ORDERS+'/api/orders',401)
    for name,tokens in [('Alice',alice),('Bob',bob)]:
        call(name+' customer inquiry',CUSTOMERS+'/api/customers',200,tokens['access_token'])
        call(name+' customer detail',CUSTOMERS+'/api/customers/C100',200,tokens['access_token'])
        call(name+' order inquiry',ORDERS+'/api/orders',200,tokens['access_token'])
    call('ID token is not an API access token',ORDERS+'/api/orders',401,alice['id_token'])
    call('Invalid bearer token',ORDERS+'/api/orders',401,'invalid-token')
    call('Alice update denied',ORDERS+'/api/orders/O100',403,alice['access_token'],'PUT',{'status':'SHIPPED'})
    call('Alice delete denied',ORDERS+'/api/orders/O200',403,alice['access_token'],'DELETE')
    order,_=call('Denied update left data unchanged',ORDERS+'/api/orders/O100',200,alice['access_token'])
    assert order['status']=='NEW','Restart Order API before running this test'
    call('Bob invalid body',ORDERS+'/api/orders/O100',400,bob['access_token'],'PUT',{})
    order,_=call('Bob update allowed',ORDERS+'/api/orders/O100',200,bob['access_token'],'PUT',{'status':'SHIPPED'})
    assert order['status']=='SHIPPED'
    order,_=call('Alice can read updated order',ORDERS+'/api/orders/O100',200,alice['access_token'])
    assert order['status']=='SHIPPED'
    call('Bob delete allowed',ORDERS+'/api/orders/O200',204,bob['access_token'],'DELETE')
    call('Deleted order missing',ORDERS+'/api/orders/O200',404,bob['access_token'])
    origin=os.environ.get('FRONTEND_ORIGIN','http://localhost:5173')
    _,headers=call('Browser preflight',ORDERS+'/api/orders/O100',200,method='OPTIONS',headers={'Origin':origin,'Access-Control-Request-Method':'PUT','Access-Control-Request-Headers':'authorization,content-type'})
    assert headers.get('Access-Control-Allow-Origin')==origin
    print('All real-Keycloak authorization checks passed.')
if __name__=='__main__':main()
