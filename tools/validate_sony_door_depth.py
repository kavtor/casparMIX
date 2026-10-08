from PIL import Image
import math
"""Validate Sony 1041–1048 far/near hinged entry, reversal, endpoints and MV identity."""
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
  pixels=np.zeros((720,1280,3),dtype=np.uint8)
  pixels[:,:,0]=np.round(np.arange(1280)[None,:]*255/1279).astype(np.uint8)
  pixels[:,:,1]=np.round(np.arange(720)[:,None]*255/719).astype(np.uint8)
  for channel,blue in [(1,64),(2,128)]:
   pixels[:,:,2]=blue;texture=root/f'uv-{channel}.png';Image.fromarray(pixels).save(texture);cmd(f'PLAY {channel}-1 "{texture}"')
  time.sleep(.2)
  for code in range(1041,1049):
   for reverse in (False,True):
    cmd('PLAY 3-1 route://1 RENDERED');time.sleep(.1)
    cmd(f'PLAY 3-1 route://2 RENDERED DMENATIVE 25 SONY_{code} MANUAL 1 REVERSE {int(reverse)}')
    cmd('PLAY 4-1 route://3 RENDERED');cmd('MIXER 4-1 FILL 0 0 .5 1')
    for progress in (.25,.75):
     cmd(f'CALL 3-1 "PROGRESS {progress}"');time.sleep(.1)
     result=capture(f'{code}-{int(reverse)}-{progress}')
     t=1-progress if reverse else progress
     phase=(code-1041)%4;horizontal=phase<2;hinge=1 if phase in (1,3) else 0
     angle=(1-t)*math.pi/2;aspect=1280/720
     checks=[]
     for u,v in ((.25,.25),(.75,.25),(.75,.75),(.25,.75),(.5,.5)):
      px=(u-.5)*aspect;py=v-.5;offset=(u if horizontal else v)-hinge
      z=(-1 if code<=1044 else 1)*abs(offset)*(aspect if horizontal else 1)*math.sin(angle)
      if horizontal:px=((hinge-.5)+offset*math.cos(angle))*aspect
      else:py=(hinge-.5)+offset*math.cos(angle)
      scale=3.5/(3.5-z);ix=round((.5+px*scale/aspect)*1279);iy=round((.5+py*scale)*719)
      if not (2<=ix<1278 and 2<=iy<718):continue
      expected=np.array([round(255*u),round(255*v),64 if reverse else 128])
      sample=capture.rgb[iy,ix].astype(int)
      assert np.max(np.abs(sample-expected))<=5,(code,reverse,progress,u,v,sample.tolist(),expected.tolist())
      checks.append({'uv':[u,v],'pixel':[ix,iy],'sample':sample.tolist()})
     assert checks
     result['texture_checks']=checks;results[f'{code}-{int(reverse)}-{progress}']=result
    for progress in (0,1):
     cmd(f'CALL 3-1 "PROGRESS {progress}"');time.sleep(.1)
     capture(f'{code}-{int(reverse)}-endpoint-{progress}')
     assert abs(int(capture.rgb[360,640,2])-(64 if progress==0 else 128))<=2
    print('VERIFIED DOOR DEPTH',code,'REV' if reverse else 'NORM',flush=True)
 finally:
  proc.stdin.write(b'q\n');proc.stdin.flush()
  try:proc.wait(timeout=8)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=8)
(root/'results.json').write_text(json.dumps(results,indent=2))
