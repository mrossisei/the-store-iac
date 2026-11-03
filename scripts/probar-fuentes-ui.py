#!/usr/bin/env python3
"""T09: captura pasiva de fuentes ALB/kubelet, sin cambiar pods ni políticas."""
import argparse,base64,http.client,ipaddress,json,os,socket,subprocess,sys,time,uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0,'scripts')
from acceso_kind import ROOT,private_write,require,validate_manifest
from ssm import aws,run
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--manifest',default=os.environ.get('THE_STORE_ACCESS_MANIFEST'))
parser.add_argument('--baseline',required=True,type=Path)
parser.add_argument('--evidence',required=True,type=Path)
parser.add_argument('--namespace',default='the-store')
args=parser.parse_args()
os.umask(0o077)
require(bool(args.manifest),'Usar scripts/acceso.py run')
validate_manifest(args.manifest)
access=json.loads(Path(args.manifest).read_text())
baseline=json.loads(args.baseline.read_text())
require(baseline.get('status')=='PASS' and baseline.get('phase') in ('baseline','quarantine','restored'),'Requiere evidencia T09 aprobada')
require('.local' in args.evidence.resolve().parts,'Guardar evidencia bajo .local')
folder=args.evidence.resolve().parent
folder.mkdir(parents=True,exist_ok=True,mode=0o700)
folder.chmod(0o700)
env=json.loads((ROOT/'config/entorno.json').read_text())
lb=json.loads(subprocess.check_output(['terraform','-chdir='+str(ROOT/'terraform/infra'),'output','-json','load_balancer'],text=True,timeout=240))
require(set(lb['target_ids'].values())=={e['instance_id'] for e in access['clusters'].values()},'ALB y acceso apuntan a distintas instancias')
coord={'compute':access['clusters'],'load_balancer':lb}
marker='__t09_source_'+uuid.uuid4().hex
REMOTE=r'''
import ctypes,os,select,socket,struct,subprocess,time
config='/var/lib/the-store/kubeconfig'
def kube(*args):
 return json.loads(subprocess.check_output(['kubectl','--kubeconfig',config,*args,'-o','json'],text=True))
assert kube('get','namespace','kube-system')['metadata']['uid']==payload['uid']
pods=[p for p in kube('get','pods','-n',payload['namespace'],'-l','app=ui')['items'] if not p['metadata'].get('deletionTimestamp')]
assert {p['metadata']['name']:p['metadata']['uid'] for p in pods}==payload['pods']
assert pods and all(p['status']['phase']=='Running' for p in pods)
ips={p['status']['podIP'] for p in pods}
nodes=kube('get','nodes')['items']
internal={a['address'] for n in nodes for a in n['status']['addresses'] if a['type']=='InternalIP'}
tunnels={v for n in nodes for k,v in n['metadata'].get('annotations',{}).items() if k in ('projectcalico.org/IPv4IPIPTunnelAddr','projectcalico.org/IPv4VXLANTunnelAddr')}
libc=ctypes.CDLL(None,use_errno=True)
libc.setns.argtypes=[ctypes.c_int,ctypes.c_int]
libc.setns.restype=ctypes.c_int
host=os.open('/proc/self/ns/net',os.O_RDONLY)
sockets=[]
records=[]
counts={}
def enter(fd):
 if libc.setns(fd,0x40000000)!=0:raise OSError(ctypes.get_errno(),'setns failed')
try:
 for name in {p['spec']['nodeName'] for p in pods}:
  assert name in {payload['cluster_name']+'-control-plane',payload['cluster_name']+'-worker'}
  pid=int(subprocess.check_output(['docker','inspect','-f','{{.State.Pid}}',name],text=True))
  fd=os.open('/proc/'+str(pid)+'/ns/net',os.O_RDONLY)
  try:
   enter(fd)
   sock=socket.socket(socket.AF_PACKET,socket.SOCK_RAW,socket.htons(0x0003));sock.setblocking(False)
   sockets.append(sock)
  finally:
   enter(host);os.close(fd)
 deadline=time.monotonic()+payload['duration']
 while time.monotonic()<deadline:
  active,_,_=select.select(sockets,[],[],0.5)
  for sock in active:
   try:frame=sock.recv(65535)
   except BlockingIOError:continue
   for offset in (14,18,22,0,4,16,20):
    if len(frame)<offset+40 or frame[offset]>>4!=4 or frame[offset+9]!=6:continue
    ihl=(frame[offset]&15)*4
    if ihl<20 or len(frame)<offset+ihl+20:continue
    destination=socket.inet_ntoa(frame[offset+16:offset+20])
    if destination not in ips:continue
    tcp=offset+ihl
    sport,dport=struct.unpack('!HH',frame[tcp:tcp+4])
    if dport!=8080:continue
    content=frame[tcp+((frame[tcp+12]>>4)*4):]
    if not content.startswith(b'GET '):continue
    path=content.split(b' ',2)[1].decode('ascii','replace')
    lower=content.lower()
    if payload['marker'] in path:kind='marked-alb'
    elif path=='/actuator/health/readiness' and b'user-agent: kube-probe/' in lower:kind='kubelet-probe'
    elif path=='/actuator/health/readiness' and b'user-agent: elb-healthchecker/' in lower:kind='alb-health'
    else:continue
    bucket=(kind,destination)
    if counts.get(bucket,0)>=3:continue
    counts[bucket]=counts.get(bucket,0)+1
    records.append({'kind':kind,'source_ip':socket.inet_ntoa(frame[offset+12:offset+16]),'source_port':sport,'destination_ip':destination,'destination_port':dport,'path':path})
    break
finally:
 for sock in sockets:sock.close()
 os.close(host)
print(json.dumps({'cluster_uid':payload['uid'],'pods':{p['metadata']['name']:{'uid':p['metadata']['uid'],'ip':p['status']['podIP'],'node':p['spec']['nodeName']} for p in pods},'node_internal_ips':sorted(internal),'node_tunnel_ips':sorted(tunnels),'records':records}))
'''
def capture(key):
 entry=coord['compute'][key]
 expected=baseline['clusters'][key]['after']
 require(expected['cluster_uid']==entry['cluster_uid'],'Cambió identidad del clúster '+key)
 expected_pods={name:p['uid'] for name,p in expected['pods'].items() if any(c['name']=='ui' for c in p['containers'])}
 require(bool(expected_pods),'Faltan pods UI en baseline')
 payload={'uid':entry['cluster_uid'],'cluster_name':entry['cluster_name'],'namespace':args.namespace,'pods':expected_pods,'marker':marker,'duration':35}
 code='import json,base64\npayload=json.loads(base64.b64decode('+repr(base64.b64encode(json.dumps(payload).encode()).decode())+'))\n'+REMOTE
 output=run(env['region'],entry['instance_id'],"set -eu\npython3 - <<'CAPTURE_PY'\n"+code+"\nCAPTURE_PY\n",folder/('packet-source-'+key+'.log'),timeout=120)
 result=json.loads(output)
 ips={p['ip'] for p in result['pods'].values()}
 require(any(r['kind']=='marked-alb' for r in result['records']),'Falta solicitud ALB marcada en '+key)
 for kind in ('alb-health','kubelet-probe'):
  require({r['destination_ip'] for r in result['records'] if r['kind']==kind}==ips,'Falta captura '+kind+' en '+key)
 for record in result['records']:
  ip=ipaddress.ip_address(record['source_ip'])
  within=any(ip in ipaddress.ip_network(env['kind'][field]) for field in ('pod_cidr','service_cidr'))
  require(not within or record['source_ip'] in set(result['node_internal_ips']+result['node_tunnel_ips']),'Origen no contemplado por policyUI')
 return result
report={'status':'FAIL','marker':marker,'public_requests':0,'clusters':{}}
connection=http.client.HTTPConnection(coord['load_balancer']['dns_name'],timeout=10)
try:
 with ThreadPoolExecutor(max_workers=2) as pool:
  futures={key:pool.submit(capture,key) for key in ('a','b')}
  deadline=time.monotonic()+120
  while not all(f.done() for f in futures.values()) and time.monotonic()<deadline:
   connection.request('GET','/'+marker)
   response=connection.getresponse();response.read()
   require(response.status in (200,404),'ALB no sirve UI')
   report['public_requests']+=1
   time.sleep(0.2)
  errors=[]
  for key,future in futures.items():
   try:report['clusters'][key]=future.result()
   except Exception as exc:errors.append(exc)
  if errors:raise errors[0]
 targets=aws(env['region'],'elbv2','describe-target-health','--target-group-arn',coord['load_balancer']['target_group_arn'])['TargetHealthDescriptions']
 require({t['Target']['Id'] for t in targets}==set(coord['load_balancer']['target_ids'].values()) and all(t['TargetHealth']['State']=='healthy' for t in targets),'Targets ALB no healthy')
 report['alb_targets']={t['Target']['Id']:t['TargetHealth']['State'] for t in targets}
 report['status']='PASS'
 print('PASS: requests ALB marcados en ambos kind y health ALB/kubelet en las cuatro UI, sin cambios en pods.',flush=True)
finally:
 connection.close()
 private_write(args.evidence,json.dumps(report,indent=2)+'\n')
