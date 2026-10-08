from PIL import Image
import math
"""Compare final program pixels with an equally sized tile in a wide rendered multiview."""
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
  codes=list(range(1051,1059))+list(range(1061,1065))+[1068]
  pixels=np.zeros((720,1280,3),dtype=np.uint8)
  pixels[:,:,0]=np.round(np.arange(1280)[None,:]*255/1279).astype(np.uint8);pixels[:,:,1]=np.round(np.arange(720)[:,None]*255/719).astype(np.uint8)
  for ch,blue in [(1,64),(2,128)]:
   pixels[:,:,2]=blue;texture=root/f'uv-{ch}.png';Image.fromarray(pixels).save(texture);cmd(f'PLAY {ch}-1 "{texture}"')
  time.sleep(.2)
  for code in codes:
   cmd('PLAY 3-1 route://1-1');time.sleep(.1);cmd(f'PLAY 3-1 route://2 RENDERED DMENATIVE 25 SONY_{code} MANUAL 1');cmd('PLAY 4-1 route://3 RENDERED');cmd('MIXER 4-1 FILL 0 0 .5 1')
   for progress in [.25,.75]:
    cmd(f'CALL 3-1 "PROGRESS {progress}"');time.sleep(.1);result=capture(f'{code}-{progress}')
    px=py=cx=cy=.5
    if code<=1058:
     clockwise=code<=1054;phase=code-1051 if clockwise else code-1055;px,py=[(0,1),(0,0),(1,0),(1,1)][phase];cx,cy=px,py;angle=(-1 if clockwise else 1)*(1-progress)*math.pi/2
    elif code==1068:cy=1-progress/2;angle=-(1-progress)*2*math.pi
    else:
     px=cx=1 if code in [1062,1063] else 0;py=.5;cy=1-progress/2 if code in [1063,1064] else progress/2;angle=(1 if code in [1061,1063] else -1)*(1-progress)*math.pi/2
    checks=[]
    for u in np.linspace(.05,.95,10):
     for v in np.linspace(.05,.95,10):
      x=(u-px)*(1280/720)*progress;y=(v-py)*progress
      screenX=cx+(x*math.cos(angle)-y*math.sin(angle))/(1280/720);screenY=cy+x*math.sin(angle)+y*math.cos(angle)
      if not (3/1280<screenX<1-3/1280 and 3/720<screenY<1-3/720):continue
      ix=round(screenX*1279);iy=round(screenY*719);sample=capture.rgb[iy,ix].astype(int);expected=np.array([round(255*u),round(255*v),128])
      assert np.max(np.abs(sample-expected))<=4,(code,progress,u,v,sample.tolist(),expected.tolist())
      checks.append({'uv':[u,v],'pixel':[ix,iy],'sample':sample.tolist()})
    assert len(checks)>=2,(code,progress,'no visible texture checks');result['texture_check_count']=len(checks);result['max_channel_error']=max(max(abs(row['sample'][i]-([round(255*row['uv'][0]),round(255*row['uv'][1]),128][i])) for i in range(3)) for row in checks);result['representative_checks']=checks[:2]+checks[-2:];results[f'{code}-{progress}']=result
   print('VERIFIED PLANAR TEXTURE',code,flush=True)

 finally:
  proc.stdin.write(b'q\n');proc.stdin.flush()
  try:proc.wait(timeout=8)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=8)
(root/'results.json').write_text(json.dumps(results,indent=2))
