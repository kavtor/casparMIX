"""Compare final program pixels with an equally sized tile in a wide rendered multiview."""
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
  gray=np.round(np.arange(1280)[None,:]*255/1279).astype(np.uint8);gray=np.repeat(gray,720,axis=0)
  pixels=np.repeat(gray[:,:,None],3,axis=2);texture=root/'gray.png';Image.fromarray(pixels).save(texture)
  cmd('PLAY 1-1 #0000ff');cmd(f'PLAY 2-1 "{texture}"');time.sleep(.3)
  cmd('PLAY 3-1 route://1-1');cmd('PLAY 3-2 route://2-1');cmd('PLAY 4-1 route://3 RENDERED');cmd('MIXER 4-1 FILL 0 0 .5 1');time.sleep(.2)
  g=gray.astype(float)/255;coverage=np.clip((g-.25)/.5,0,1)
  cases=[('luma',0,0,0),('luma-inverse',1,0,0),('mask',0,1,0),('mask-inverse',0,1,1)]
  xx=(np.arange(1280)[None,:]+.5)/1280;yy=(np.arange(720)[:,None]+.5)/720
  inside=(xx>=.2)&(xx<.8)&(yy>=.1)&(yy<.6)
  for name,invert,mask,maskInvert in cases:
   command=f'MIXER 3-2 ALPHAKEY LUMA .25 .75 {invert} {mask} {maskInvert} .2 .1 .8 .6';cmd(command);time.sleep(.1);result=capture(name)
   alpha=1-coverage if invert else coverage
   if mask:alpha=alpha*(~inside if maskInvert else inside)
   expected=np.stack([g*alpha,g*alpha,g*alpha+1-alpha],axis=2)*255
   error=np.abs(capture.rgb.astype(float)-expected)
   assert np.max(error)<=3,(name,float(np.max(error)),np.unravel_index(np.argmax(error),error.shape))
   result['max_pixel_error']=float(np.max(error));results[name]=result;print('VERIFIED ALPHA KEY',name,flush=True)
  before=results['mask-inverse']['sha256']
  for value in ['nan','0.25x','1']:
   s.sendall((f'MIXER 3-2 ALPHAKEY LUMA {value} .75 0 1 1 .2 .1 .8 .6\r\n').encode());assert f.readline().decode().startswith('4')
  result=capture('invalid-preserves-state');assert result['sha256']==before;results['invalid']=result
  cmd('MIXER 3-2 ALPHAKEY OFF 0 1 0 0 0 .1 .1 .9 .9');time.sleep(.1);result=capture('reset');assert np.max(np.abs(capture.rgb.astype(int)-pixels.astype(int)))<=2;results['reset']=result
  # A key modifies its logical layer, never the shared prepared input.
  path=root/'shared-source.mkv';cmd(f'ADD 2 FILE "{path}" -codec:v ffv1');time.sleep(.4);cmd(f'REMOVE 2 FILE "{path}"');time.sleep(.2)
  data=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vf','select=eq(n\\,8)','-frames:v','1','-pix_fmt','rgb24','-f','rawvideo','-']);source=np.frombuffer(data,dtype=np.uint8).reshape(720,1280,3)
  assert np.max(np.abs(source.astype(int)-pixels.astype(int)))<=2
  results['shared_source_unchanged']=True
  rgba=np.zeros((720,1280,4),dtype=np.uint8);rgba[:,:,1]=255;rgba[:,:,3]=gray
  texture=root/'alpha-ramp.png';Image.fromarray(rgba).save(texture);cmd(f'PLAY 2-1 "{texture}"');time.sleep(.25)
  for inverse in [0,1]:
   cmd(f'MIXER 3-2 ALPHAKEY LINEAR 0 1 {inverse} 0 0 .1 .1 .9 .9');time.sleep(.1);result=capture(f'linear-{inverse}')
   alpha=1-g if inverse else g;expected=np.stack([np.zeros_like(g),alpha,1-alpha],axis=2)*255
   # Premultiplied sources carry no recoverable fill where their original alpha
   # is exactly zero. Check the remaining ramp, including nearly transparent ink.
   error=np.abs(capture.rgb[:,gray[0]>0].astype(float)-expected[:,gray[0]>0]);assert np.max(error)<=3,('linear',inverse,float(np.max(error)))
   result['max_pixel_error']=float(np.max(error));results[f'linear-{inverse}']=result
  colour=np.zeros((720,1280,3),dtype=np.uint8);colour[:,:640,1]=255;colour[:,640:,0]=255
  texture=root/'green-red.png';Image.fromarray(colour).save(texture);cmd(f'PLAY 2-1 "{texture}"');time.sleep(.25)
  cmd('MIXER 3-2 CHROMA 1 120 .1 .1 .1 .05 30 1 0')
  for inverse in [0,1]:
   cmd(f'MIXER 3-2 ALPHAKEY LINEAR 0 1 {inverse} 0 0 .1 .1 .9 .9');time.sleep(.1);result=capture(f'chroma-{inverse}')
   assert np.max(np.abs(capture.rgb[360,320].astype(int)-np.array([0,255,0] if inverse else [0,0,255])))<=3
   assert np.max(np.abs(capture.rgb[360,960].astype(int)-np.array([0,0,255] if inverse else [255,0,0])))<=3
   results[f'chroma-{inverse}']=result


 finally:
  proc.stdin.write(b'q\n');proc.stdin.flush()
  try:proc.wait(timeout=8)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=8)
(root/'results.json').write_text(json.dumps(results,indent=2))
