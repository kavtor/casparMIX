import argparse,array,math,json,socket,time,subprocess
from pathlib import Path
parser=argparse.ArgumentParser(description='Capture and validate native textured page deformation on an isolated server.')
parser.add_argument('--binary',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
a=parser.parse_args()
root=a.output.resolve();root.mkdir(parents=True,exist_ok=True)
for d in ['media','log','data','template']:(root/d).mkdir(exist_ok=True)
with socket.socket() as p:p.bind(('127.0.0.1',0));port=p.getsockname()[1]
config=root/'caspar.config';config.write_text('<configuration><paths>'+''.join(f'<{d}-path>{root}/{d}</{d}-path>' for d in ['media','log','data','template'])+'</paths><ndi><auto-load>false</auto-load></ndi><channels>'+('<channel><video-mode>720p5000</video-mode><sync-group>dme-test</sync-group></channel>'*3)+f'</channels><controllers><tcp><port>{port}</port><protocol>AMCP</protocol></tcp></controllers></configuration>')
for name,colour,hz in [('red','red',400),('green','lime',1000)]:
 subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i',f'color=c={colour}:s=640x360:r=50:d=3','-f','lavfi','-i',f'sine=frequency={hz}:sample_rate=48000:duration=3','-c:v','ffv1','-pix_fmt','bgra','-c:a','pcm_s16le','-shortest',str(root/'media'/f'{name}.mkv')],check=True)
log=(root/'server.log').open('w');proc=subprocess.Popen([str(a.binary.resolve()),str(config)],cwd=root,stdin=subprocess.PIPE,stdout=log,stderr=log)
results={}
try:
 for i in range(100):
  try:s=socket.create_connection(('127.0.0.1',port),.2);break
  except OSError:time.sleep(.2)
 s.settimeout(15);f=s.makefile('rb');transcript=(root/'amcp.log').open('w')
 def cmd(c):
  s.sendall((c+'\r\n').encode());reply=f.readline().decode().strip();transcript.write(c+' -> '+reply+'\n');transcript.flush()
  if not reply.startswith('2'):raise RuntimeError(reply)
  if reply.startswith('201'):f.readline()
 def capture(name):
  path=root/(name+'.mkv');cmd(f'ADD 3 FILE "{path}" -codec:v ffv1 -codec:a pcm_s16le');time.sleep(.8);cmd(f'REMOVE 3 FILE "{path}"');time.sleep(.4)
  data=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vf','select=eq(n\\,15)','-frames:v','1','-pix_fmt','bgra','-f','rawvideo','-'])
  subprocess.run(['ffmpeg','-y','-v','error','-i',str(path),'-vf','select=eq(n\\,15)','-frames:v','1',str(root/(name+'.png'))],check=True)
  return data
 def pixel(data,x,y):
  i=(int(y*720)*1280+int(x*1280))*4;b,g,r,a=data[i:i+4];return(r,g,b)
 cmd('PLAY 1-1 red.mkv LOOP');cmd('PLAY 2-1 green.mkv LOOP');cmd('PLAY 3-1 route://1-1');time.sleep(.3)
 full={'fill':[0,0,1,1],'clip':[0,0,1,1],'crop':[0,0,1,1],'opacity':1,'volume':1,'order':0};end={**full,'fill':[0,0,.5,1],'clip':[0,0,.5,1]};green={**full,'fill':[.5,0,.5,1],'clip':[.5,0,.5,1],'volume':0,'order':1}
 manifest=[{'producer':'route://1-1','from':full,'to':end},{'producer':'route://2-1','from':{**green,'opacity':0},'to':green}]
 # destination is the same prepared two-up composition as the manifest endpoint
 cmd('PLAY 2-2 route://1-1');cmd('MIXER 2-1 VOLUME 0');cmd('MIXER 2-1 FILL .5 0 .5 1');cmd('MIXER 2-2 FILL 0 0 .5 1')
 scene=json.dumps(manifest,separators=(',',':')).encode().hex()
 cmd(f'PLAY 3-1 route://2 RENDERED DMENATIVE 25 MOVE MANUAL 1 SCENE {scene}');time.sleep(.3)
 for p in [0,.5,1,0]:
  cmd(f'CALL 3-1 "PROGRESS {p}"');time.sleep(.2);data=capture(f'move-{p}-{len(results)}');left,right=pixel(data,.1,.5),pixel(data,.9,.5)
  if p==0:assert left[0]>240 and right[0]>240,(left,right)
  if p==1:assert left[0]>240 and right[1]>240,(left,right)
  if p==.5:
   path=root/f'move-{p}-{len(results)}.mkv'
   pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:a:0','-ac','1','-ar','48000','-f','f32le','-']);samples=array.array('f');samples.frombytes(pcm);samples=samples[4800:24000]
   def amplitude(hz):
    return 2*math.hypot(sum(v*math.cos(2*math.pi*hz*i/48000) for i,v in enumerate(samples)),sum(v*math.sin(2*math.pi*hz*i/48000) for i,v in enumerate(samples)))/len(samples)
   red_audio,green_audio=amplitude(400),amplitude(1000);assert red_audio>.01 and green_audio<red_audio*.1,(red_audio,green_audio)
   results['audio']={'matched_source':red_audio,'muted_source':green_audio}
  results[f'move-{p}-{len(results)}']={'left':left,'right':right}
 cmd('CLEAR 2-2');cmd('MIXER 2-1 CLEAR')
 for effect in ['PAGE_CURL','PAGE_CURL_REVERSE','PAGE_ROLL','PAGE_ROLL_REVERSE']:
  cmd('PLAY 3-1 route://1-1');time.sleep(.2);cmd(f'PLAY 3-1 route://2 RENDERED DMENATIVE 25 {effect.removesuffix("_REVERSE")} MANUAL 1 REVERSE {int(effect.endswith("_REVERSE"))}');time.sleep(.2)
  cmd('CALL 3-1 "PROGRESS .5"');time.sleep(.2);data=capture(effect.lower());left,right=pixel(data,.25,.5),pixel(data,.75,.5);top,bottom=pixel(data,.5,.25),pixel(data,.5,.75)
  red=lambda p:p[0]>240 and p[1]<10
  green=lambda p:p[1]>240 and p[0]<10
  if effect in ['CUBE','PUSH_RIGHT','SLIDE_RIGHT']:assert red(left) and green(right),(effect,left,right)
  if effect in ['CUBE_REVERSE','PUSH_LEFT','SLIDE_LEFT']:assert green(left) and red(right),(effect,left,right)
  if effect.endswith('_TOP'):assert green(top) and red(bottom),(effect,top,bottom)
  if effect.endswith('_BOTTOM'):assert red(top) and green(bottom),(effect,top,bottom)
  if effect=='ZOOM':assert 120<=left[0]<=135 and 120<=left[1]<=135,(effect,left)
  white=sum(1 for n in range(0,len(data),4) if min(data[n:n+3])>130 and max(data[n:n+3])-min(data[n:n+3])<4)
  assert white<32,(effect,white)
  cmd('CALL 3-1 "PROGRESS 1"');time.sleep(.1);end=capture(effect.lower()+'-end');assert pixel(end,.5,.5)[1]>240
  cmd('CALL 3-1 "PROGRESS 0"');time.sleep(.1);start=capture(effect.lower()+'-rewind');assert pixel(start,.5,.5)[0]>240
  results[effect]={'neutral_paper_pixels':white,'live_backside':True,'endpoint':True,'rewind':True}
 cmd('PLAY 3-1 route://1-1');time.sleep(.2);cmd('PLAY 3-1 route://2 RENDERED DMENATIVE 25 CUBE MANUAL 0');time.sleep(1);data=capture('cube-auto-end');assert pixel(data,.9,.5)[1]>240
 results['auto_endpoint']=True
 cmd('PLAY 3-1 route://1-1');time.sleep(.2);blue='#0000ff'.encode().hex()
 cmd(f'PLAY 3-1 route://2 RENDERED DMENATIVE 25 CUBE MANUAL 1 BACKGROUND {blue}')
 cmd('CALL 3-1 "PROGRESS .5"');time.sleep(.2);data=capture('cube-blue-background');assert pixel(data,.01,.01)[2]>240
 red='#ff0000'.encode().hex();cmd(f'CALL 3-1 "BACKGROUND {red}"');time.sleep(.2);data=capture('cube-live-background');assert pixel(data,.01,.01)[0]>240
 results['background']={'solid_colour':True,'live_change':True}
 bg='route://1 RENDERED'.encode().hex();cmd(f'CALL 3-1 "BACKGROUND {bg}"');time.sleep(.2);data=capture('cube-video-background');assert pixel(data,.01,.01)[0]>240
 pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(root/'cube-video-background.mkv'),'-map','0:a:0','-ac','1','-ar','48000','-f','f32le','-']);samples=array.array('f');samples.frombytes(pcm);samples=samples[4800:24000]
 level=amplitude(400);assert .035<level<.055,level
 results['background']['video_signal_muted']=True
 cmd('CALL 3-1 "PROGRESS 1"');time.sleep(.1)

 try:cmd('PLAY 3-1 route://1-1 DMENATIVE 25 MOVE MANUAL 1 SCENE zz')
 except RuntimeError:results['invalid_scene_rejected']=True
 else:raise AssertionError('Malformed scene accepted')
 data=capture('invalid-scene-retains-program');assert pixel(data,.5,.5)[1]>240
 results['invalid_scene_retains_program']=True
finally:
 proc.stdin.write(b'q\n');proc.stdin.flush()
 try:proc.wait(timeout=8)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=8)
 log.close()
(root/'results.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
