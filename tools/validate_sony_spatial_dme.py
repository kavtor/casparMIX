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
  codes=list(range(1045,1049))+list(range(1101,1105))+[1121,1122]
  backdrop='#00ff00'.encode().hex()
  for code in codes:
   cmd('PLAY 3-1 route://1-1');time.sleep(.1)
   cmd(f'PLAY 3-1 route://2 RENDERED DMENATIVE 25 SONY_{code} MANUAL 1 BACKGROUND '+backdrop)
   cmd('PLAY 4-1 route://3 RENDERED');cmd('MIXER 4-1 FILL 0 0 .5 1');time.sleep(.12)
   poses={};images={}
   for progress in [0,.25,.5,.75,1]:
    cmd(f'CALL 3-1 "PROGRESS {progress}"');time.sleep(.1);poses[str(progress)]=capture(f'{code}-{progress}');images[progress]=capture.rgb.copy()
    if progress==0:assert np.all(capture.rgb==[255,0,0]),code
    elif progress==1:assert np.all(capture.rgb==[0,0,255]),code
    elif code>=1101:
     if progress==.5:assert np.all(capture.rgb==[0,255,0]),code
     else:
      face=0 if progress<.5 else 2
      assert np.count_nonzero(capture.rgb[:,:,face]>220)>10000,code
      assert np.count_nonzero((capture.rgb[:,:,1]>220)&(capture.rgb[:,:,face]<20))>10000,code
    else:assert poses[str(progress)]['direct']['red']>500 and poses[str(progress)]['direct']['blue']>500,code
   cmd('CALL 3-1 "PROGRESS .25"');time.sleep(.1);rewind=capture(f'{code}-rewind')
   assert np.array_equal(images[.25],capture.rgb),('rewind',code)
   cmd('PLAY 3-1 route://1-1');time.sleep(.1)
   cmd(f'PLAY 3-1 route://2 RENDERED DMENATIVE 25 SONY_{code} MANUAL 1 REVERSE 1 BACKGROUND '+backdrop)
   cmd('CALL 3-1 "PROGRESS .25"');time.sleep(.1);reverse=capture(f'{code}-reverse')
   assert np.array_equal(images[.75][:,:,::-1],capture.rgb),('reverse',code)
   results[str(code)]={'poses':poses,'rewind':rewind,'reverse':reverse};print('VERIFIED SPATIAL SONY DME',code,flush=True)

 finally:
  proc.stdin.write(b'q\n');proc.stdin.flush()
  try:proc.wait(timeout=8)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=8)
(root/'results.json').write_text(json.dumps(results,indent=2))
