"""Validate native inner/outer wipe borders and independent softness."""
import argparse,json,socket,subprocess,time,hashlib,numpy as np
from PIL import Image
import math
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
  cmd('PLAY 3-1 route://1 RENDERED');time.sleep(.1)
  cmd('PLAY 3-1 route://2 RENDERED WIPESONY 25 SONY 1 MANUAL 1 BORDER 10 BORDERCOLOR #00ff00')
  cmd('PLAY 4-1 route://3 RENDERED');cmd('MIXER 4-1 FILL 0 0 .5 1')
  for side in (0,-1,1):
   cmd(f'CALL 3-1 "PROGRESS .5 BORDER_SIDE {side} INNER_SOFT 0 OUTER_SOFT 0"');time.sleep(.1);result=capture('side-'+str(side))
   rgb=capture.rgb.astype(int);green=rgb[:,:,1]>220;ys,xs=np.where(green);assert len(xs)>1000
   center=float(xs.mean());assert (abs(center-639.5)<2 if side==0 else center<630 if side<0 else center>650),(side,center)
   assert np.max(np.abs(rgb.sum(axis=2)-255))<=3,'Border partition loses brightness'
   result['green_centroid_x']=center;results[str(side)]=result
   cmd(f'CALL 3-1 "INNER_SOFT 15 OUTER_SOFT 3"');time.sleep(.1);soft=capture('soft-'+str(side));rgb=capture.rgb.astype(int);assert np.max(np.abs(rgb.sum(axis=2)-255))<=3
   # Require the actual A/color/B weights, not merely conserved brightness.
   # Red=A, green=border, blue=B; the whole-frame matte uses pixel centers.
   d=(.5-(np.arange(1280)+.5)/1280)*(1280/720)
   def coverage(distance,width):
    u=np.clip((distance+width)/(2*width),0,1)
    return u*u*(3-2*u)
   border=10/540
   inner_width=0 if side==1 else 2*border if side==-1 else border
   outer_width=0 if side==-1 else 2*border if side==1 else border
   inner=coverage(d-inner_width,15/270)
   outer=np.maximum(inner,coverage(d+outer_width,3/270))
   expected=np.stack((1-outer,outer-inner,inner),axis=1)*255
   error=float(np.max(np.abs(rgb[360].astype(float)-expected)))
   assert error<=4,('A/color/B partition is contaminated',side,error)
   result['maximum_partition_error_rgb8']=error
   result['soft']=soft;before=capture.rgb.copy()
   s.sendall(b'CALL 3-1 "BORDER_SIDE 0 INNER_SOFT 101"\r\n');reply=f.readline().decode().strip();assert reply.startswith('4'),reply
   time.sleep(.1);capture('invalid-'+str(side));assert np.array_equal(before,capture.rgb),'Invalid profile changed prepared geometry'
  cmd('CALL 3-1 "PROGRESS 0"');time.sleep(.1);results['start']=capture('start');assert np.min(capture.rgb[:,:,0])>252
  cmd('CALL 3-1 "PROGRESS 1"');time.sleep(.1);results['end']=capture('end');assert np.min(capture.rgb[:,:,2])>252
  print('VERIFIED asymmetric border placement, soft color partition, atomic rejection, endpoints and PGM/MV identity',flush=True)

 finally:
  proc.stdin.write(b'q\n');proc.stdin.flush()
  try:proc.wait(timeout=8)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=8)
(root/'results.json').write_text(json.dumps(results,indent=2))
