"""Validate native Karaoke 220-223 row phasing and rendered MV identity."""
from PIL import Image
import argparse,json,socket,subprocess,time,hashlib,numpy as np
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--binary',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--baseline',action='store_true');args=p.parse_args();root=args.output.resolve();root.mkdir(parents=True,exist_ok=True)
for d in ['media','data','log','template']:(root/d).mkdir(exist_ok=True)
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
mode='<video-modes><video-mode><id>iris-wide</id><width>2560</width><height>720</height><time-scale>50</time-scale><duration>1</duration></video-mode></video-modes>'
channels=''.join('<channel><sync-group>iris</sync-group><video-mode>'+('iris-wide' if ch==4 else '720p5000')+'</video-mode></channel>' for ch in range(1,5))
config=root/'caspar.config';config.write_text('<configuration><paths>'+''.join(f'<{d}-path>{root}/{d}</{d}-path>' for d in ['media','data','log','template'])+'</paths><ndi><auto-load>false</auto-load></ndi>'+mode+'<channels>'+channels+f'</channels><controllers><tcp><port>{port}</port><protocol>AMCP</protocol></tcp></controllers></configuration>')
results={}
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
    data=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vf','select=eq(n\\,8)','-frames:v','1','-pix_fmt','rgb24','-f','rawvideo','-']);assert len(data)==width*720*3
    picture=b''.join(data[y*width*3:y*width*3+1280*3] for y in range(720));pictures.append(picture)
    pixels=np.frombuffer(picture,dtype=np.uint8).reshape(720,1280,3)
    red=(pixels[:,:,0]>220)&(pixels[:,:,2]<30);blue=(pixels[:,:,2]>220)&(pixels[:,:,0]<30)
    out.append({'red':int(red.sum()),'blue':int(blue.sum())})
    if ch==3:capture.rgb=pixels.copy()
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(path),'-vf','select=eq(n\\,8)','-frames:v','1',str(root/f'{name}-{ch}.png')],check=True)
   assert pictures[0]==pictures[1], 'Rendered multiview pixels differ from program'
   return {'direct':out[0],'rendered_multiview':out[1],'identical_rgb_pixels':True,'sha256':hashlib.sha256(pictures[0]).hexdigest()}
  cmd('PLAY 1-1 #ff0000');cmd('PLAY 2-1 #0000ff');time.sleep(.2)
  for code in range(220,224):
   cmd('PLAY 3-1 route://1 RENDERED');time.sleep(.1);cmd(f'PLAY 3-1 route://2 RENDERED WIPESONY 25 SONY {code} MANUAL 1');cmd('PLAY 4-1 route://3 RENDERED');cmd('MIXER 4-1 FILL 0 0 .5 1');time.sleep(.1)
   poses={};previous=-1;held=None;three_quarters=None
   for progress in [0,.1,.25,.5,.75,.9,1,.5]:
    cmd(f'CALL 3-1 "PROGRESS {progress}"');time.sleep(.1);result=capture(f'{code}-{progress}-{len(poses)}')
    assert np.max(np.abs(capture.rgb.astype(int).sum(axis=2)-255))<=2
    coverage=float(capture.rgb[:,:,2].mean()/255)
    if progress==0:assert coverage<.001
    if progress==1:assert coverage>.999
    if progress!=.5 or held is None:assert coverage>=previous;previous=coverage
    if progress==.75:three_quarters=capture.rgb.copy()
    if progress==.5:
     if held is not None:assert np.array_equal(held,capture.rgb)
     held=capture.rgb.copy()
    result['blue_fraction']=coverage;poses[str(progress)+'-'+str(len(poses))]=result
   cmd('CALL 3-1 "PROGRESS .25 PHASE -100 ROWNO 8 START -100"');time.sleep(.1);sim=capture(f'{code}-simultaneous')
   blue=capture.rgb[:,:,2]>220
   lane=blue.mean(axis=1 if code<222 else 0)
   assert lane.max()-lane.min()<.01,(code,float(lane.max()-lane.min()))
   if code==220:assert blue[:,0].all() and not blue[:,-1].any()
   if code==221:assert blue[:,-1].all() and not blue[:,0].any()
   if code==222:assert blue[0,:].all() and not blue[-1,:].any()
   if code==223:assert blue[-1,:].all() and not blue[0,:].any()
   cmd('CALL 3-1 "PROGRESS .05 PHASE 100 START -100"');time.sleep(.1);first=capture(f'{code}-start-first');ys,xs=np.where(capture.rgb[:,:,2]>220);assert len(xs)>1000
   center=float(ys.mean()/720 if code<222 else xs.mean()/1280);assert center<.125
   cmd('CALL 3-1 "START 100"');time.sleep(.1);last=capture(f'{code}-start-last');ys,xs=np.where(capture.rgb[:,:,2]>220);center=float(ys.mean()/720 if code<222 else xs.mean()/1280);assert center>.875
   before=capture.rgb.copy();s.sendall(b'CALL 3-1 "START -100 ROWNO 0"\r\n');reply=f.readline().decode().strip();assert reply.startswith('4'),reply
   time.sleep(.1);capture(f'{code}-invalid');assert np.array_equal(before,capture.rgb),'Invalid update changed prepared rows'
   cmd('CALL 3-1 "PROGRESS .5 START -100 PHASE 0 SOFT 8 BORDER 5 BORDERCOLOR #00ff00"');time.sleep(.1);soft=capture(f'{code}-soft-border');assert np.max(np.abs(capture.rgb.astype(int).sum(axis=2)-255))<=3
   density={}
   for rows in [1,64]:
    cmd(f'CALL 3-1 "PROGRESS .5 ROWNO {rows} SOFT 100 BORDER 100"');time.sleep(.1)
    density[str(rows)]=capture(f'{code}-density-{rows}')
    assert np.max(np.abs(capture.rgb.astype(int).sum(axis=2)-255))<=3
    assert float((capture.rgb[:,:,1]>220).mean())<.35,'Border exceeded the actual cell width'
   cmd('PLAY 3-1 route://2 RENDERED');time.sleep(.1);cmd(f'PLAY 3-1 route://1 RENDERED WIPESONY 25 SONY {code} MANUAL 1 REVERSE 1')
   cmd('CALL 3-1 "PROGRESS .25"');time.sleep(.1);reverse=capture(f'{code}-reverse');assert np.max(np.abs(capture.rgb.astype(int)-three_quarters.astype(int)))<=1,'REV does not retrace NORM within 8-bit blend rounding'
   cmd('PLAY 3-1 route://1 RENDERED');time.sleep(.1);cmd(f'PLAY 3-1 route://1 RENDERED WIPESONY 25 SONY {code} MANUAL 1');cmd('CALL 3-1 "PROGRESS .5"');time.sleep(.1);same=capture(f'{code}-same-source');assert np.min(capture.rgb[:,:,0])>=253 and np.max(capture.rgb[:,:,1:])<=2
   cmd('PLAY 3-1 route://1 RENDERED');time.sleep(.1);cmd(f'PLAY 3-1 route://2 RENDERED WIPESONY 10 SONY {code}');time.sleep(.5);auto=capture(f'{code}-auto');assert np.min(capture.rgb[:,:,2])>=253
   results[str(code)]={'density_extremes':density,'reverse':reverse,'same_source':same,'auto_endpoint':auto,'poses':poses,'simultaneous':sim,'first_lane':first,'last_lane':last,'soft_border':soft,'atomic_invalid_update':True};print('VERIFIED SONY KARAOKE',code,flush=True)
  print('VERIFIED karaoke endpoints, monotonicity, rewind, four orientations, phase extremes, start lanes, atomic updates, soft/border and exact PGM/MV identity',flush=True)

 finally:
  proc.stdin.write(b'q\n');proc.stdin.flush()
  try:proc.wait(timeout=8)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=8)
(root/'results.json').write_text(json.dumps(results,indent=2))
