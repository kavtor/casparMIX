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
  pixels=np.zeros((720,1280,3),dtype=np.uint8)
  pixels[:,:,1]=np.round(np.arange(1280)[None,:]*255/1279).astype(np.uint8)
  pixels[:,:,2]=np.round(np.arange(720)[:,None]*255/719).astype(np.uint8)
  texture=root/'uv-grid.png';Image.fromarray(pixels).save(texture)
  cmd(f'PLAY 2-1 "{texture}"');time.sleep(.2)
  positions={1021:(.125,.25),1022:(.625,.25),1023:(.25,.125),1024:(.25,.625),1025:(.125,.125),1026:(.625,.125),1027:(.625,.625),1028:(.125,.625),1029:(.375,.25),1030:(.25,.375),1031:(.375,.375)}
  for code in list(positions)+list(range(1041,1045)):
   cmd('PLAY 3-1 route://1-1');time.sleep(.08);cmd(f'PLAY 3-1 route://2 RENDERED DMENATIVE 25 SONY_{code} MANUAL 1');time.sleep(.1);cmd('CALL 3-1 "PROGRESS .5"');cmd('PLAY 4-1 route://3 RENDERED');cmd('MIXER 4-1 FILL 0 0 .5 1');time.sleep(.1)
   result=capture(str(code))
   if code<1041:x,y=positions[code]
   else:
    horizontal=code<1043;hinge=1 if code in (1042,1044) else 0;offset=.25-hinge;angle=math.pi/4
    px=(.25-.5)*1280/720;py=.25-.5
    z=-abs(offset)*(1280/720 if horizontal else 1)*math.sin(angle)
    if horizontal:px=((hinge-.5)+offset*math.cos(angle))*1280/720
    else:py=(hinge-.5)+offset*math.cos(angle)
    scale=3.5/(3.5-z);x=.5+px*scale/(1280/720);y=.5+py*scale
   sample=capture.rgb[int(y*720),int(x*1280)].astype(int)
   assert abs(sample[1]-64)<5 and abs(sample[2]-64)<5,(code,x,y,sample.tolist())
   results[str(code)]={'sample':sample.tolist(),'expected_uv':[.25,.25],'capture':result};print('VERIFIED UV TRANSFORM',code,flush=True)
 finally:
  proc.stdin.write(b'q\n');proc.stdin.flush()
  try:proc.wait(timeout=8)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=8)
(root/'results.json').write_text(json.dumps(results,indent=2))
