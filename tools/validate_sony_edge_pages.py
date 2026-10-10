"""Validate Sony edge page/roll texture directions, endpoints and rendered MV identity."""
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
  cmd('PLAY 1-1 #101010')
  pixels=np.zeros((720,1280,3),dtype=np.uint8);pixels[:,:,0]=np.round(np.arange(1280)[None,:]*255/1279);pixels[:,:,1]=np.round(np.arange(720)[:,None]*255/719);pixels[:,:,2]=255
  texture=root/'page-grid.png';Image.fromarray(pixels).save(texture);cmd(f'PLAY 2-1 "{texture}"');time.sleep(.2)
  for code in [1301,1302,1303,1304,1321,1322,1323,1324]:
   cmd('PLAY 3-1 route://1 RENDERED');time.sleep(.1);cmd(f'PLAY 3-1 route://2 RENDERED DMENATIVE 25 SONY_{code} MANUAL 1');cmd('PLAY 4-1 route://3 RENDERED');cmd('MIXER 4-1 FILL 0 0 .5 1');time.sleep(.1)
   poses={};mid=None
   for progress in [0,.25,.5,.75,1,.5]:
    cmd(f'CALL 3-1 "PROGRESS {progress}"');time.sleep(.1);result=capture(f'{code}-{progress}-{len(poses)}')
    if progress==0:assert np.max(np.abs(capture.rgb.astype(int)-16))<=1
    if progress==1:assert np.max(np.abs(capture.rgb.astype(int)-pixels.astype(int)))<=3
    if progress==.5:
     if mid is not None:assert np.array_equal(capture.rgb,mid),'Manual rewind changed the mesh'
     mid=capture.rgb.copy()
     visible=capture.rgb[:,:,2]>100;ys,xs=np.where(visible);assert len(xs)>5000 and len(xs)<850000,(code,len(xs))
     direction=code%100-1
     center=float(xs.mean()/1280 if direction<2 else ys.mean()/720)
     assert center>.5 if direction in [0,2] else center<.5,(code,center)
     result['incoming_centroid']=center
     assert np.any((capture.rgb[:,:,2]>100)&(capture.rgb[:,:,2]<245)), 'Missing shaded live texture'
    poses[str(progress)+'-'+str(len(poses))]=result
   # REV is the exact time-reversed path with A/B roles exchanged.
   cmd('PLAY 3-1 route://2 RENDERED');time.sleep(.1);cmd(f'PLAY 3-1 route://1 RENDERED DMENATIVE 25 SONY_{code} MANUAL 1 REVERSE 1')
   cmd('CALL 3-1 "PROGRESS .5"');time.sleep(.1);rev=capture(f'{code}-reverse-mid');assert np.array_equal(capture.rgb,mid),'REV does not retrace the same textured path'
   cmd('CALL 3-1 "PROGRESS 1"');time.sleep(.1);end=capture(f'{code}-reverse-end');assert np.max(np.abs(capture.rgb.astype(int)-16))<=1
   cmd('PLAY 3-1 route://1 RENDERED');time.sleep(.1);cmd(f'PLAY 3-1 route://2 RENDERED DMENATIVE 10 SONY_{code}');time.sleep(.5);auto=capture(f'{code}-auto-end');assert np.max(np.abs(capture.rgb.astype(int)-pixels.astype(int)))<=3
   results[str(code)]={'poses':poses,'reverse_retraces':rev,'reverse_endpoint':end,'auto_endpoint':auto};print('VERIFIED SONY EDGE PAGE',code,flush=True)

 finally:
  proc.stdin.write(b'q\n');proc.stdin.flush()
  try:proc.wait(timeout=8)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=8)
(root/'results.json').write_text(json.dumps(results,indent=2))
