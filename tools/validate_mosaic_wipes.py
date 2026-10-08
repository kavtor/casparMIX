"""Measure producer-raster iris proportions directly and in a wide raw-route multiview."""
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
    pixels=np.frombuffer(picture,dtype=np.uint8).reshape(720,1280,3);blue=(pixels[:,:,2]>220)&(pixels[:,:,0]<30);red=(pixels[:,:,0]>220)&(pixels[:,:,2]<30)
    out.append({'blue_pixels':int(blue.sum()),'red_pixels':int(red.sum())})
    if ch==3:capture.last_blue=blue
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(path),'-vf','select=eq(n\\,8)','-frames:v','1',str(root/f'{name}-{ch}.png')],check=True)
   assert pictures[0]==pictures[1], 'Rendered multiview pixels differ from program'
   return {'direct':out[0],'rendered_multiview':out[1],'identical_rgb_pixels':True,'sha256':hashlib.sha256(pictures[0]).hexdigest()}
  cmd('PLAY 1-1 #ff0000');cmd('PLAY 2-1 #0000ff');time.sleep(.2)
  codes=[200,201,202,203,206,207,208,209,210,211,212,213]
  width,height,side=1280,720,144
  nx,ny=9,5
  def path(code):
   if code==200:return [(x,y) for y in range(ny) for x in (range(nx) if y%2==0 else range(nx-1,-1,-1))]
   if code==201:return [(x,y) for x in range(nx) for y in (range(ny) if x%2==0 else range(ny-1,-1,-1))]
   if code in (202,203):
    order=[]
    for diagonal in range(nx+ny-1):
     cells=[(x,diagonal-x) for x in range(nx) if 0<=diagonal-x<ny]
     if diagonal%2==0:cells.reverse()
     order.extend(cells)
    return order if code==202 else [(nx-1-x,y) for x,y in order]
   # Walk the outer perimeter, rotate at each boundary, shrink by visited cells.
   corner=(code-206)%4;cw=code<210
   x,y=[(0,0),(nx-1,0),(nx-1,ny-1),(0,ny-1)][corner]
   directions=[(1,0),(0,1),(-1,0),(0,-1)]
   direction=corner if cw else (corner+1)%4
   turn=1 if cw else -1;order=[];seen=set()
   for _ in range(nx*ny):
    order.append((x,y));seen.add((x,y));dx,dy=directions[direction];xx,yy=x+dx,y+dy
    if not(0<=xx<nx and 0<=yy<ny) or (xx,yy) in seen:
     direction=(direction+turn)%4;dx,dy=directions[direction];xx,yy=x+dx,y+dy
    x,y=xx,yy
   assert len(set(order))==nx*ny
   return order
  for code in codes:
   cmd('PLAY 3-1 route://1-1');time.sleep(.08);cmd(f'PLAY 3-1 route://2 RENDERED WIPESONY 25 SONY {code} MANUAL 1 TILESIZE 20');time.sleep(.1);cmd('PLAY 4-1 route://3 RENDERED');cmd('MIXER 4-1 FILL 0 0 .5 1')
   order=path(code);results[str(code)]={}
   for progress in [.25,.5,.75]:
    cmd(f'CALL 3-1 "PROGRESS {progress}"');time.sleep(.1);result=capture(f'{code}-{progress}');mask=capture.last_blue
    exposed=set(order[:int(progress*nx*ny)])
    for y in range(ny):
     for x in range(nx):
      # Check four interior points, including edge tiles clipped by the raster.
      lo_x,hi_x=x*side,min((x+1)*side,width);lo_y,hi_y=y*side,min((y+1)*side,height)
      for u,v in [(.25,.25),(.75,.25),(.25,.75),(.75,.75)]:
       px=int(lo_x+(hi_x-lo_x)*u);py=int(lo_y+(hi_y-lo_y)*v)
       assert bool(mask[py,px])==((x,y) in exposed),(code,progress,x,y)
    results[str(code)][str(progress)]=result
   cmd('CALL 3-1 "PROGRESS .5 REVERSE 1"');time.sleep(.1);results[str(code)]['reverse']=capture(f'{code}-reverse')
   cmd('CALL 3-1 "PROGRESS .5 REVERSE 0 TILESIZE 10"');time.sleep(.1);results[str(code)]['size_live']=capture(f'{code}-size10')
   print('VERIFIED MOSAIC',code,flush=True)
 finally:
  proc.stdin.write(b'q\n');proc.stdin.flush()
  try:proc.wait(timeout=8)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=8)
(root/'results.json').write_text(json.dumps(results,indent=2))
