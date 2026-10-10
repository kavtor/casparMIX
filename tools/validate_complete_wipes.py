"""Validate all newly completed Sony WIPE paths and rendered MV identity."""
from PIL import Image
import argparse,json,socket,subprocess,time,hashlib,numpy as np
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--binary',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--baseline',action='store_true');p.add_argument('--resume',action='store_true',help='Skip patterns in an existing checked results.json');args=p.parse_args();root=args.output.resolve();root.mkdir(parents=True,exist_ok=True)
for d in ['media','data','log','template']:(root/d).mkdir(exist_ok=True)
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
mode='<video-modes><video-mode><id>iris-wide</id><width>2560</width><height>720</height><time-scale>50</time-scale><duration>1</duration></video-mode></video-modes>'
channels=''.join('<channel><sync-group>iris</sync-group><video-mode>'+('iris-wide' if ch==4 else '720p5000')+'</video-mode></channel>' for ch in range(1,5))
config=root/'caspar.config';config.write_text('<configuration><paths>'+''.join(f'<{d}-path>{root}/{d}</{d}-path>' for d in ['media','data','log','template'])+'</paths><ndi><auto-load>false</auto-load></ndi>'+mode+'<channels>'+channels+f'</channels><controllers><tcp><port>{port}</port><protocol>AMCP</protocol></tcp></controllers></configuration>')
results=json.loads((root/'results.json').read_text()) if args.resume and (root/'results.json').exists() else {}
with (root/'server.log').open('w') as log:
 proc=subprocess.Popen([str(args.binary.resolve()),str(config)],cwd=root,stdin=subprocess.PIPE,stdout=log,stderr=log)
 try:
  for _ in range(100):
   try:s=socket.create_connection(('127.0.0.1',port),.2);break
   except OSError:time.sleep(.2)
  s.settimeout(10);f=s.makefile('rb')
  def cmd(c):
   s.sendall((c+'\r\n').encode());reply=f.readline().decode().strip();assert reply.startswith('2'),(c,reply)
   return f.readline().decode().strip() if reply.startswith('201') else ''
  results['version']=cmd('VERSION')
  def capture(name):
   paths=[root/f'{name}-{ch}.mkv' for ch in (3,4)]
   for ch,path in zip((3,4),paths):cmd(f'ADD {ch} FILE "{path}" -codec:v ffv1')
   time.sleep(.4)
   for ch,path in zip((3,4),paths):cmd(f'REMOVE {ch} FILE "{path}"')
   time.sleep(.15);out=[];pictures=[]
   for ch,path in zip((3,4),paths):
    width=1280 if ch==3 else 2560
    # FILE removal acknowledges before its async encoder has fully drained.
    # Wait for a complete decoded frame instead of assuming 150 ms is enough.
    decode=['ffmpeg','-v','error','-i',str(path),'-vf','select=eq(n\\,8)','-frames:v','1','-pix_fmt','rgb24','-f','rawvideo','-']
    for attempt in range(30):
     data=subprocess.check_output(decode,stderr=subprocess.DEVNULL)
     if len(data)==width*720*3:break
     time.sleep(.1)
    assert len(data)==width*720*3,(path,len(data))
    picture=b''.join(data[y*width*3:y*width*3+1280*3] for y in range(720));pictures.append(picture)
    pixels=np.frombuffer(picture,dtype=np.uint8).reshape(720,1280,3)
    red=(pixels[:,:,0]>220)&(pixels[:,:,2]<30);blue=(pixels[:,:,2]>220)&(pixels[:,:,0]<30)
    out.append({'red':int(red.sum()),'blue':int(blue.sum())})
    if ch==3:capture.rgb=pixels.copy()
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(path),'-vf','select=eq(n\\,8)','-frames:v','1',str(root/f'{name}-{ch}.png')],check=True)
   assert pictures[0]==pictures[1], 'Rendered multiview pixels differ from program'
   return {'direct':out[0],'rendered_multiview':out[1],'identical_rgb_pixels':True,'sha256':hashlib.sha256(pictures[0]).hexdigest()}
  cmd('PLAY 1-1 #ff0000');cmd('PLAY 2-1 #0000ff');time.sleep(.2)
  for code in list(range(224,248))+[270,271,272]:
   if str(code) in results:continue
   cmd('PLAY 3-1 route://1 RENDERED');time.sleep(.1)
   cmd(f'PLAY 3-1 route://2 RENDERED WIPESONY 25 SONY {code} MANUAL 1')
   cmd('PLAY 4-1 route://3 RENDERED');cmd('MIXER 4-1 FILL 0 0 .5 1');time.sleep(.1)
   poses={};previous=-1;held=None;reverse_reference=None
   for index,progress in enumerate([0,.1,.25,.5,.75,.9,1,.5]):
    cmd(f'CALL 3-1 "PROGRESS {progress}"');time.sleep(.1);result=capture(f'{code}-{progress}-{index}')
    assert np.max(np.abs(capture.rgb.astype(int).sum(axis=2)-255))<=2
    coverage=float(capture.rgb[:,:,2].mean()/255)
    if progress==0:assert coverage<.001
    if progress==1:assert coverage>.999
    if index<7:assert coverage>=previous;previous=coverage
    if progress==.75:reverse_reference=capture.rgb.copy()
    if progress==.5:
     if held is not None:assert np.array_equal(held,capture.rgb)
     held=capture.rgb.copy()
    result['blue_fraction']=coverage;poses[str(index)]=result
   capture(f'{code}-hold');assert np.array_equal(held,capture.rgb)
   before=capture.rgb.copy();s.sendall(b'CALL 3-1 "PROGRESS .25 H_SIZE 0"\r\n');reply=f.readline().decode().strip();assert reply.startswith('4'),reply
   time.sleep(.1);capture(f'{code}-invalid');assert np.array_equal(before,capture.rgb)
   cmd('CALL 3-1 "PROGRESS .5 SOFT 8 BORDER 5 BORDERCOLOR #00ff00"');time.sleep(.1);border=capture(f'{code}-border')
   assert np.max(np.abs(capture.rgb.astype(int).sum(axis=2)-255))<=3
   assert float((capture.rgb[:,:,1]>220).mean())<.65
   cmd('PLAY 3-1 route://2 RENDERED');time.sleep(.1)
   cmd(f'PLAY 3-1 route://1 RENDERED WIPESONY 25 SONY {code} MANUAL 1 REVERSE 1');cmd('CALL 3-1 "PROGRESS .25"');time.sleep(.1)
   reverse=capture(f'{code}-reverse');assert np.max(np.abs(capture.rgb.astype(int)-reverse_reference.astype(int)))<=1
   cmd('PLAY 3-1 route://1 RENDERED');time.sleep(.1)
   cmd(f'PLAY 3-1 route://1 RENDERED WIPESONY 25 SONY {code} MANUAL 1');cmd('CALL 3-1 "PROGRESS .5"');time.sleep(.1)
   same=capture(f'{code}-same');assert np.min(capture.rgb[:,:,0])>=253 and np.max(capture.rgb[:,:,1:])<=2
   cmd('PLAY 3-1 route://1 RENDERED');time.sleep(.1);cmd(f'PLAY 3-1 route://2 RENDERED WIPESONY 10 SONY {code}');time.sleep(.5)
   auto=capture(f'{code}-auto');assert np.min(capture.rgb[:,:,2])>=253
   results[str(code)]={'poses':poses,'hold_rewind':True,'atomic_rejection':True,'reverse':reverse,'border':border,'same_source':same,'auto':auto}
   (root/'results.json').write_text(json.dumps(results,indent=2))
   print('VERIFIED SONY COMPLETE',code,flush=True)
  # Existing Dust Mix syntax still works after completing the inventory.
  cmd('PLAY 3-1 route://1 RENDERED');time.sleep(.1);cmd('PLAY 3-1 route://2 RENDERED DUSTMIX 25 MANUAL 1 DUST_RATIO 1 H_SIZE .02 V_SIZE .02 FLASH_RATE 0');cmd('CALL 3-1 "PROGRESS .5"');time.sleep(.1)
  results['dustmix']=capture('dustmix-independent')
  print('VERIFIED exact endpoints, monotonicity, hold/rewind, reverse, brightness, border, atomic rejection, independent Dust Mix and exact PGM/MV identity',flush=True)
 finally:
  proc.stdin.write(b'q\n');proc.stdin.flush()
  try:proc.wait(timeout=8)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=8)
(root/'results.json').write_text(json.dumps(results,indent=2))
