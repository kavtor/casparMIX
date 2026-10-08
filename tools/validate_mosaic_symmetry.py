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
  if proc.poll() is not None:raise RuntimeError("Test renderer exited during startup; inspect server.log")
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
  codes=list(range(250,258))+list(range(260,270))
  width,height=1280,720
  def snake(w,h,vertical):
   return [(x,y) for x in range(w) for y in (range(h) if x%2==0 else range(h-1,-1,-1))] if vertical else [(x,y) for y in range(h) for x in (range(w) if y%2==0 else range(w-1,-1,-1))]
  def spiral(w,h,vertical):
   dirs=[(0,1),(1,0),(0,-1),(-1,0)] if vertical else [(1,0),(0,1),(-1,0),(0,-1)]
   x=y=d=0;seen=set();order=[]
   for _ in range(w*h):
    order.append((x,y));seen.add((x,y));dx,dy=dirs[d];xx,yy=x+dx,y+dy
    if not(0<=xx<w and 0<=yy<h) or (xx,yy) in seen:d=(d+1)%4;dx,dy=dirs[d];xx,yy=x+dx,y+dy
    x,y=xx,yy
   return order
  def thresholds(code,nx,ny):
   result={}
   def region(w,h,order,map_cell):
    for i,c in enumerate(order):
     cell=map_cell(*c);result[cell]=min(result.get(cell,1.0),i/(w*h))
   if code<=253:
    w=(nx+1)//2;h=ny
    for side in [0,1]:
     flip_y=code==251 or code==252 and side==1 or code==253 and side==0
     region(w,h,snake(w,h,True),lambda x,y,side=side,flip_y=flip_y:(x if side==0 else nx-1-x,ny-1-y if flip_y else y))
   elif code<=257:
    w=nx;h=(ny+1)//2
    for side in [0,1]:
     flip_x=code==255 or code==256 and side==1 or code==257 and side==0
     region(w,h,snake(w,h,False),lambda x,y,side=side,flip_x=flip_x:(nx-1-x if flip_x else x,y if side==0 else ny-1-y))
   elif code<=265:
    xs=[0,1] if code in (260,261,264,265) else [0]
    ys=[0,1] if code in (262,263,264,265) else [0]
    w=(nx+1)//2 if len(xs)==2 else nx;h=(ny+1)//2 if len(ys)==2 else ny
    for xx in xs:
     for yy in ys:
      mx=xx==1 or code==263;my=yy==1 or code==261
      region(w,h,spiral(w,h,code in (260,261,264)),lambda x,y,mx=mx,my=my:(nx-1-x if mx else x,ny-1-y if my else y))
   else:
    for y in range(ny):
     for x in range(nx):
      lane=x if code==266 else nx-1-x if code==267 else y if code==268 else ny-1-y
      length=ny if code<268 else nx;lanes=nx if code<268 else ny
      cell=y if code<268 else x if code==268 else nx-1-x
      span=min(3,lanes);result[(x,y)]=(lane+cell/length*span)/(lanes+span)
   return result
  for size in [10,20,25]:
   side=height*size/100;nx=int(np.ceil(width/side));ny=int(np.ceil(height/side));ox=(nx*side-width)/2;oy=(ny*side-height)/2
   for code in codes:
    cmd('PLAY 3-1 route://1-1');time.sleep(.05);cmd(f'PLAY 3-1 route://2 RENDERED WIPESONY 25 SONY {code} MANUAL 1 TILESIZE {size}');time.sleep(.07);cmd('PLAY 4-1 route://3 RENDERED');cmd('MIXER 4-1 FILL 0 0 .5 1')
    order=thresholds(code,nx,ny);results[f'{code}-size{size}']={}
    cmd('CALL 3-1 "PROGRESS .5"');time.sleep(.08);result=capture(f'{code}-{size}');mask=capture.last_blue
    exposed={cell for cell,t in order.items() if t<int(.5*nx*ny)/(nx*ny)}
    for y in range(ny):
     for x in range(nx):
      lo_x,hi_x=max(0,x*side-ox),min((x+1)*side-ox,width);lo_y,hi_y=max(0,y*side-oy),min((y+1)*side-oy,height)
      for u,v in [(.25,.25),(.75,.25),(.25,.75),(.75,.75)]:
       px=int(lo_x+(hi_x-lo_x)*u);py=int(lo_y+(hi_y-lo_y)*v)
       assert bool(mask[py,px])==((x,y) in exposed),(code,size,x,y)
    if code in [250,251,260,261,264,265]:assert np.array_equal(mask,np.fliplr(mask)),(code,size,'horizontal symmetry')
    if code in [254,255,262,263,264,265]:assert np.array_equal(mask,np.flipud(mask)),(code,size,'vertical symmetry')
    result['grid']=[nx,ny];result['centered_edge_clipping']=True;results[f'{code}-size{size}']=result;print('VERIFIED CENTERED MOSAIC',code,size,flush=True)
 finally:
  if proc.poll() is None:proc.stdin.write(b'q\n');proc.stdin.flush()
  try:proc.wait(timeout=8)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=8)
(root/'results.json').write_text(json.dumps(results,indent=2))
