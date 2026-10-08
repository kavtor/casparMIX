"""Validate supported Sony wipe geometry from captured native frames."""
import argparse,json,math,socket,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--binary',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=a.output.resolve();root.mkdir(parents=True,exist_ok=True)
for d in ('media','log','data','template'):(root/d).mkdir(exist_ok=True)
with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
config=root/'caspar.config';config.write_text('<configuration><paths>'+''.join(f'<{d}-path>{root}/{d}</{d}-path>' for d in ('media','log','data','template'))+'</paths><ndi><auto-load>false</auto-load></ndi><channels>'+('<channel><video-mode>720p5000</video-mode><sync-group>sony</sync-group></channel>'*3)+f'</channels><controllers><tcp><port>{port}</port><protocol>AMCP</protocol></tcp></controllers></configuration>')
def distance(c,x,y,t):
 if c==1:return t-x
 if c==2:return t-1+x
 if c==3:return t-y
 if c==4:return t-1+y
 if c in (5,6,7,8):return t-max(x if c in (5,8) else 1-x,y if c in (5,6) else 1-y)
 if c in (9,10,11,12):return 2*t-(x if c in (9,12) else 1-x)-(y if c in (9,10) else 1-y)
 dx,dy=abs(x-.5)*16/9,abs(y-.5);ex,ey=8/9,.5
 if c==17:return t*ex-dx
 if c==18:return t*ey-dy
 if c==21:return t*ex-max(dx,dy)
 if c==22:return max(t*ex-dx,t*ey-dy)
 if c==23:return t*(ex+ey)-dx-dy
 return t*math.hypot(ex,ey)-math.hypot(dx,dy)
results={}
with (root/'server.log').open('w') as log:
 proc=subprocess.Popen([str(a.binary.resolve()),str(config)],cwd=root,stdin=subprocess.PIPE,stdout=log,stderr=log)
 try:
  for _ in range(100):
   try:s=socket.create_connection(('127.0.0.1',port),.2);break
   except OSError:time.sleep(.2)
  s.settimeout(10);f=s.makefile('rb')
  def cmd(text):
   s.sendall((text+'\r\n').encode());reply=f.readline().decode();assert reply.startswith('2'),(text,reply)
   if reply.startswith('201'):f.readline()
  cmd('PLAY 1-1 #ff0000');cmd('PLAY 2-1 #0000ff');time.sleep(.3)
  for code in (1,2,3,4,5,6,7,8,9,10,11,12,17,18,21,22,23,24):
   cmd('PLAY 3-1 route://1-1');time.sleep(.05);cmd(f'PLAY 3-1 route://2-1 WIPESONY 1 SONY {code} MANUAL 1 SOFT 0 BORDER 0');time.sleep(.08)
   total=0
   for progress in (.25,.5,.75):
    cmd(f'CALL 3-1 "PROGRESS {progress}"');time.sleep(.08)
    path=root/f'{code}-{progress}.mkv';cmd(f'ADD 3 FILE "{path}" -codec:v ffv1');time.sleep(.35);cmd(f'REMOVE 3 FILE "{path}"');time.sleep(.08)
    data=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vf','select=eq(n\\,8)','-frames:v','1','-pix_fmt','rgb24','-f','rawvideo','-']);assert len(data)==1280*720*3
    for row in range(18):
     for col in range(32):
      px,py=20+col*40,20+row*40;d=distance(code,(px+.5)/1280,(py+.5)/720,progress)
      if abs(d)<.015:continue
      r,g,b=data[(py*1280+px)*3:(py*1280+px)*3+3];assert (b>240 and r<10) if d>0 else (r>240 and b<10),(code,progress,px,py,d,(r,g,b));total+=1
   results[str(code)]={'samples':total,'progress':[.25,.5,.75],'geometry':True};print('VERIFIED',code,flush=True)
 finally:
  proc.stdin.write(b'q\n');proc.stdin.flush()
  try:proc.wait(timeout=8)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=8)
(root/'results.json').write_text(json.dumps(results,indent=2))
