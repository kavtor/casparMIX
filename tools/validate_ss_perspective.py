"""Validate supported Sony wipe geometry from captured native frames."""
import argparse,json,math,socket,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--binary',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=a.output.resolve();root.mkdir(parents=True,exist_ok=True)
for d in ('media','log','data','template'):(root/d).mkdir(exist_ok=True)
with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
config=root/'caspar.config';config.write_text('<configuration><paths>'+''.join(f'<{d}-path>{root}/{d}</{d}-path>' for d in ('media','log','data','template'))+'</paths><ndi><auto-load>false</auto-load></ndi><channels>'+('<channel><video-mode>720p5000</video-mode><sync-group>sony</sync-group></channel>'*7)+f'</channels><controllers><tcp><port>{port}</port><protocol>AMCP</protocol></tcp></controllers></configuration>')
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
  cmd('PLAY 7-0 #000000');cmd('PLAY 7-1 route://1-1');cmd('MIXER 7-1 FILL .1 .1 .4 .4');cmd('MIXER 7-1 CLIP .1 .1 .4 .4');cmd('MIXER 7-1 PERSPECTIVE .125 0 .875 0 1.125 1 -.125 1');cmd('PLAY 3-1 route://7 RENDERED');time.sleep(.3)
  path=root/'perspective.mkv';cmd(f'ADD 3 FILE "{path}" -codec:v ffv1');time.sleep(.4);cmd(f'REMOVE 3 FILE "{path}"');time.sleep(.1)
  data=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vf','select=eq(n\\,8)','-frames:v','1','-pix_fmt','rgb24','-f','rawvideo','-'])
  def pixel(x,y):
   offset=(int(y*720)*1280+int(x*1280))*3;return list(data[offset:offset+3])
  inside=pixel(.3,.3);excluded=pixel(.12,.12);lower=pixel(.12,.48)
  assert inside==[255,0,0] and excluded==[0,0,0] and lower==[255,0,0],(inside,excluded,lower)
  subprocess.run(['ffmpeg','-y','-v','error','-i',str(path),'-vf','select=eq(n\\,8)','-frames:v','1',str(root/'perspective.png')],check=True)
  full={'fill':[0,0,1,1],'clip':[0,0,1,1],'crop':[0,0,1,1],'opacity':1,'volume':1,'order':0,'perspective':[0,0,1,0,1,1,0,1]}
  end={**full,'fill':[.1,.1,.4,.4],'clip':[.1,.1,.4,.4],'perspective':[.125,0,.875,0,1.125,1,-.125,1]}
  manifest=[{'producer':'route://1 RENDERED','from':full,'to':end}]
  cmd('PLAY 3-1 route://1-1');time.sleep(.1);cmd('PLAY 3-1 route://7 RENDERED DMENATIVE 25 MOVE MANUAL 1 SCENE '+json.dumps(manifest,separators=(',',':')).encode().hex());time.sleep(.1);cmd('CALL 3-1 "PROGRESS .999"');time.sleep(.2)
  path=root/'move-perspective.mkv';cmd(f'ADD 3 FILE "{path}" -codec:v ffv1');time.sleep(.4);cmd(f'REMOVE 3 FILE "{path}"');time.sleep(.1)
  data=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vf','select=eq(n\\,8)','-frames:v','1','-pix_fmt','rgb24','-f','rawvideo','-'])
  assert pixel(.3,.3)==[255,0,0] and pixel(.12,.12)==[0,0,0]
  results={'native_perspective':True,'move_perspective':True,'inside':inside,'excluded':excluded,'lower':lower}

 finally:
  proc.stdin.write(b'q\n');proc.stdin.flush()
  try:proc.wait(timeout=8)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=8)
(root/'results.json').write_text(json.dumps(results,indent=2))
