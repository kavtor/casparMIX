"""Measure single-copy native Sony edge page/roll audio crossfades."""
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
  for ch,frequency,colour in [(1,440,'red'),(2,880,'blue')]:
   path=root/f'tone-{ch}.mkv';subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i',f'color=c={colour}:s=1280x720:r=50','-f','lavfi','-i',f'sine=frequency={frequency}:sample_rate=48000','-t','2','-c:v','ffv1','-c:a','pcm_s16le',str(path)],check=True);cmd(f'PLAY {ch}-1 "{path}" LOOP')
  time.sleep(.5)
  cmd('PLAY 3-1 route://1 RENDERED');time.sleep(.2)
  reference=root/'reference-a.mkv';cmd(f'ADD 3 FILE "{reference}" -codec:v ffv1 -codec:a pcm_s16le');time.sleep(.6);cmd(f'REMOVE 3 FILE "{reference}"');time.sleep(.2)
  raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(reference),'-map','0:a:0','-ac','1','-ar','48000','-f','f32le','-'])
  def tone_level(audio,f):
   phase=np.arange(len(audio))/48000;window=np.hanning(len(audio))
   return 2*abs(np.sum(audio*window*np.exp(-2j*np.pi*f*phase)))/window.sum()
  baseline=tone_level(np.frombuffer(raw,dtype=np.float32)[4800:-4800],440)
  for code in [1301,1302,1303,1304,1321,1322,1323,1324]:
   cmd('PLAY 3-1 route://1-1');time.sleep(.1);cmd(f'PLAY 3-1 route://2 RENDERED DMENATIVE 25 SONY_{code} MANUAL 1')
   for progress in [.25,.5,.75]:
    cmd(f'CALL 3-1 "PROGRESS {progress}"');time.sleep(.15)
    path=root/f'{code}-{progress}.mkv';cmd(f'ADD 3 FILE "{path}" -codec:v ffv1 -codec:a pcm_s16le');time.sleep(.6);cmd(f'REMOVE 3 FILE "{path}"');time.sleep(.2)
    data=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:a:0','-ac','1','-ar','48000','-f','f32le','-'])
    audio=np.frombuffer(data,dtype=np.float32);audio=audio[4800:-4800];assert len(audio)>9600
    phase=np.arange(len(audio))/48000;window=np.hanning(len(audio))
    amplitudes=[abs(np.sum(audio*window*np.exp(-2j*np.pi*f*phase))) for f in [440,880]]
    ratio=amplitudes[1]/amplitudes[0];expected=progress/(1-progress)
    assert abs(ratio/expected-1)<.08,(code,progress,ratio,expected)
    normalized=[tone_level(audio,f)/baseline for f in [440,880]]
    assert abs(normalized[0]-(1-progress))<.04 and abs(normalized[1]-progress)<.04,(code,progress,normalized)
    results[f'{code}-{progress}']={'b_over_a_amplitude':ratio,'expected':expected,'normalized_levels':normalized};print('VERIFIED SONY EDGE PAGE AUDIO',code,progress,flush=True)

 finally:
  proc.stdin.write(b'q\n');proc.stdin.flush()
  try:proc.wait(timeout=8)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=8)
(root/'results.json').write_text(json.dumps(results,indent=2))
