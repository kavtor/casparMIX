"""Compare final program pixels with an equally sized tile in a wide rendered multiview."""
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
  cmd('PLAY 1-1 #E00000');cmd('PLAY 2-1 #0000A0');time.sleep(.15)
  for mode,extra,expected in [('NAM','',[224,0,0]),('SUPER_MIX','',[224,0,160]),('SUPER_MIX',' A_GAIN .5 B_GAIN .25',[112,0,40])]:
   cmd('PLAY 3-1 route://1-1');time.sleep(.1);cmd(f'PLAY 3-1 route://2 RENDERED DMENATIVE 25 {mode} MANUAL 1'+extra);time.sleep(.1);cmd('CALL 3-1 "PROGRESS .5"');cmd('PLAY 4-1 route://3 RENDERED');cmd('MIXER 4-1 FILL 0 0 .5 1');time.sleep(.1)
   name=mode+('-gains' if extra else '');result=capture(name);sample=capture.rgb[360,640].astype(int)
   assert np.max(np.abs(capture.rgb.astype(int)-np.array(expected)))<3,(mode,expected,sample.tolist())
   if mode=='NAM':assert sample[2]<3,'NAM must select by luminance, not component-wise MAX'
   if extra:
    cmd('CALL 3-1 "A_GAIN .4 B_GAIN .6"');time.sleep(.1);live=capture(name+'-live')
    assert np.max(np.abs(capture.rgb.astype(int)-np.array([90,0,96])))<3
    s.sendall(b'CALL 3-1 "A_GAIN .2x B_GAIN .2"\r\n');reply=f.readline().decode().strip();assert reply.startswith('4'),reply
    time.sleep(.1);invalid=capture(name+'-invalid')
    assert np.max(np.abs(capture.rgb.astype(int)-np.array([90,0,96])))<3
    result['live_gain_update']=live;result['invalid_gain_preserves_state']=invalid
   cmd('CALL 3-1 "PROGRESS 1"');time.sleep(.1);end=capture(name+'-end');assert capture.rgb[360,640,2]>155
   results[name]={'expected':expected,'sample':sample.tolist(),'mid':result,'end':end};print('VERIFIED BROADCAST MIX',name,sample.tolist(),flush=True)
 finally:
  proc.stdin.write(b'q\n');proc.stdin.flush()
  try:proc.wait(timeout=8)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=8)
(root/'results.json').write_text(json.dumps(results,indent=2))
