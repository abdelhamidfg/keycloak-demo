#!/usr/bin/env python3
"""Render an OpenShift List (JSON is also valid YAML), using only Python's standard library."""
import argparse, json, os, secrets
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument('--namespace', required=True)
p.add_argument('--apps-domain', required=True)
p.add_argument('--output', default='.runtime/openshift.json')
p.add_argument('--keycloak-url', help='Reuse an existing Keycloak server; omit its Deployment, Service and Route')
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
urls = {n: f'https://{n}-{a.namespace}.{a.apps_domain}' for n in ['keycloak','frontend','customer-api','order-api']}
if a.keycloak_url:
    urls['keycloak'] = a.keycloak_url.rstrip('/')
passwords = {k: os.environ.get(k) or secrets.token_urlsafe(24) for k in ['ADMIN_PASSWORD','ALICE_PASSWORD','BOB_PASSWORD','CUSTOMER_SECRET','ORDER_SECRET']}
realm = json.loads((root/'keycloak/realm.json').read_text())
for client in realm['clients']:
    if client['clientId'] == 'commerce-web':
        client['redirectUris'] = [urls['frontend']+'/']
        client['webOrigins'] = [urls['frontend']]
    if client['clientId'] in ['customer-api','order-api']:
        client['secret'] = passwords['CUSTOMER_SECRET' if client['clientId']=='customer-api' else 'ORDER_SECRET']
for user in realm['users']:
    user['credentials'][0]['value'] = passwords[user['username'].upper()+'_PASSWORD']
items=[]
def add(kind,name,spec=None,**kw):
    versions={'Deployment':'apps/v1','Route':'route.openshift.io/v1','BuildConfig':'build.openshift.io/v1','ImageStream':'image.openshift.io/v1'}
    obj={'apiVersion':versions.get(kind,'v1'),'kind':kind,'metadata':{'name':name,'namespace':a.namespace,'labels':{'app.kubernetes.io/part-of':'commerce-demo'}}}
    if spec is not None: obj['spec']=spec
    obj.update(kw);items.append(obj)
add('Secret','demo-credentials',type='Opaque',stringData=passwords)
add('Secret','keycloak-realm',type='Opaque',stringData={'realm.json':json.dumps(realm)})
config={'keycloakUrl':urls['keycloak'],'realm':'commerce-demo','clientId':'commerce-web','customerApiUrl':urls['customer-api'],'orderApiUrl':urls['order-api']}
add('ConfigMap','frontend-config',data={'config.js':'window.APP_CONFIG = '+json.dumps(config)+';\n'})
def secret_env(name,key):return {'name':name,'valueFrom':{'secretKeyRef':{'name':'demo-credentials','key':key}}}
for name in (['customer-api','order-api','frontend'] if a.keycloak_url else ['keycloak','customer-api','order-api','frontend']):
    if name!='keycloak':
        add('ImageStream',name)
        add('BuildConfig',name,{'source':{'type':'Binary','binary':{}},'strategy':{'type':'Docker','dockerStrategy':{'dockerfilePath':name+'/Dockerfile'}},'output':{'to':{'kind':'ImageStreamTag','name':name+':latest'}},'runPolicy':'Serial'})
    container={'name':name,'image':'quay.io/keycloak/keycloak:26.8.2' if name=='keycloak' else f'image-registry.openshift-image-registry.svc:5000/{a.namespace}/{name}:latest','imagePullPolicy':'Always','ports':[{'containerPort':8080,'name':'http'}], 'resources':{'requests':{'cpu':'100m','memory':'128Mi' if name=='frontend' else '512Mi'},'limits':{'cpu':'2','memory':'256Mi' if name=='frontend' else '1536Mi'}},'securityContext':{'allowPrivilegeEscalation':False,'capabilities':{'drop':['ALL']},'runAsNonRoot':True,'seccompProfile':{'type':'RuntimeDefault'}}}
    volumes=[]
    if name=='keycloak':
        container['args']=['start','--import-realm','--db=dev-file','--http-enabled=true','--proxy-headers=xforwarded','--health-enabled=true']
        container['env']=[{'name':'KC_HOSTNAME','value':urls['keycloak']},{'name':'KC_BOOTSTRAP_ADMIN_USERNAME','value':'admin'},secret_env('KC_BOOTSTRAP_ADMIN_PASSWORD','ADMIN_PASSWORD')]
        volumes=[{'name':'realm','secret':{'secretName':'keycloak-realm'}},{'name':'data','emptyDir':{}}]
        container['volumeMounts']=[{'name':'realm','mountPath':'/opt/keycloak/data/import','readOnly':True},{'name':'data','mountPath':'/opt/keycloak/data'}]
        probe={'httpGet':{'path':'/health/ready','port':9000},'periodSeconds':10}
        container['readinessProbe']=probe
        container['startupProbe']={**probe,'failureThreshold':60}
        container['livenessProbe']={'httpGet':{'path':'/health/live','port':9000},'periodSeconds':20}
    elif name=='frontend':
        volumes=[{'name':'config','configMap':{'name':'frontend-config'}}]
        container['volumeMounts']=[{'name':'config','mountPath':'/usr/share/nginx/html/config.js','subPath':'config.js','readOnly':True}]
        container['readinessProbe']={'httpGet':{'path':'/','port':8080}}
        container['livenessProbe']={'httpGet':{'path':'/','port':8080}}
    else:
        container['env']=[{'name':'KEYCLOAK_URL','value':urls['keycloak']},{'name':'FRONTEND_ORIGIN','value':urls['frontend']},{'name':'HTTP_PORT','value':'8080'},secret_env('CLIENT_SECRET','CUSTOMER_SECRET' if name=='customer-api' else 'ORDER_SECRET')]
        container['readinessProbe']={'httpGet':{'path':'/q/health/ready','port':8080},'periodSeconds':10}
        container['livenessProbe']={'httpGet':{'path':'/q/health/live','port':8080},'periodSeconds':20}
        container['startupProbe']={'httpGet':{'path':'/q/health/started','port':8080},'periodSeconds':10,'failureThreshold':60}
    add('Deployment',name,{'replicas':1,'strategy':{'type':'Recreate'},'selector':{'matchLabels':{'app':name}},'template':{'metadata':{'labels':{'app':name}},'spec':{'automountServiceAccountToken':False,'containers':[container],'volumes':volumes}}})
    add('Service',name,{'selector':{'app':name},'ports':[{'name':'http','port':8080,'targetPort':'http'}]})
    add('Route',name,{'host':urls[name].removeprefix('https://'),'to':{'kind':'Service','name':name},'port':{'targetPort':'http'},'tls':{'termination':'edge','insecureEdgeTerminationPolicy':'Redirect'}})
out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps({'apiVersion':'v1','kind':'List','items':items},indent=2)+'\n');out.chmod(0o600)
realm_file=out.with_name('realm.json')
realm_file.write_text(json.dumps(realm,indent=2)+'\n');realm_file.chmod(0o600)
credentials=out.with_name('demo-login.json')
logins={'alice':passwords['ALICE_PASSWORD'],'bob':passwords['BOB_PASSWORD']}
if not a.keycloak_url: logins['admin']=passwords['ADMIN_PASSWORD']
credentials.write_text(json.dumps({'urls':urls,'username_password':logins},indent=2)+'\n');credentials.chmod(0o600)
print(f'Rendered {out}. Demo login details: {credentials}. Do not commit either file.')
