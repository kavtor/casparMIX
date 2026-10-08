import argparse,subprocess,socket,time,json,xml.etree.ElementTree as E
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--binary',required=True);p.add_argument('--output',required=True);a=p.parse_args();root=Path(a.output);root.mkdir(parents=True,exist_ok=True)
for d in ['media','template','log','data']:(root/d).mkdir(exist_ok=True)
s=socket.socket();s.bind(('127.0.0.1',0));port=s.getsockname()[1];s.close()
config=root/'caspar.config';channels=''.join('<channel><sync-group>bench</sync-group><video-mode>1080p5000</video-mode></channel>' for _ in range(110));config.write_text('<configuration><paths>'+''.join(f'<{d}-path>{root}/{d}</{d}-path>' for d in ['media','template','log','data'])+'</paths><ndi><auto-load>false</auto-load></ndi><channels>'+channels+f'</channels><controllers><tcp><port>{port}</port><protocol>AMCP</protocol></tcp></controllers></configuration>')
with (root/'server.log').open('w') as log:
 proc=subprocess.Popen([a.binary,str(config)],cwd=root,stdin=subprocess.PIPE,stdout=log,stderr=log)
 try:
  for _ in range(100):
   try:s=socket.create_connection(('127.0.0.1',port),.3);break
   except OSError:time.sleep(.2)
  s.settimeout(5);f=s.makefile('rb')
  def cmd(c,xml=False):
   s.sendall((c+'\r\n').encode());h=f.readline().decode();assert h.startswith('2'),(c,h)
   if not xml:return
   b=[]
   while True:
    x=f.readline()
    if x in [b'\r\n',b'\n',b'']:break
    b.append(x)
   return E.fromstring(b''.join(b))
  for ch in range(1,7):cmd(f'PLAY {ch}-1 #44aaff')
  cmd('PLAY 109-1 route://1 RENDERED');cmd('PLAY 110-1 route://109 RENDERED');time.sleep(1)
  samples=[]
  for _ in range(6):
   r=cmd('INFO 1',True);samples.append({'wall':time.monotonic(),'epoch':int(r.find('.//frame-sync/epoch').text)});time.sleep(1)
  rate=(samples[-1]['epoch']-samples[0]['epoch'])/(samples[-1]['wall']-samples[0]['wall']);print('MEASURED FPS',rate,flush=True)
  # An empty reserved channel can activate, clear and reactivate; a rendered
  # reader of its empty stage must still receive black and a current epoch.
  cmd('PLAY 90-1 #ff0000');time.sleep(.15);r=cmd('INFO 90',True);assert r.find('.//foreground/producer') is not None
  cmd('CLEAR 90');time.sleep(.15);r=cmd('INFO 90',True);assert r.find('.//foreground/producer') is None
  cmd('PLAY 90-1 #0000ff');time.sleep(.15);r=cmd('INFO 90',True);assert r.find('.//foreground/producer') is not None
  cmd('CLEAR 90');cmd('PLAY 109-1 route://90 RENDERED');time.sleep(.15);r=cmd('INFO 90',True);assert r.find('.//frame-sync/idle') is None
  (root/'results.json').write_text(json.dumps({'fps':rate,'samples':samples,'wake_clear_reactivate_and_empty_reader':True},indent=2))
 finally:
  proc.stdin.write(b'q\n');proc.stdin.flush()
  try:proc.wait(timeout=10)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=10)
