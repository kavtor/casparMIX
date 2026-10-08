#!/usr/bin/env python3
"""Run isolated AMCP video regressions against a supplied server executable."""
import argparse
import json
from pathlib import Path
import socket
import subprocess
import tempfile
import time

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--binary',required=True,type=Path)
p.add_argument('--output',type=Path)
p.add_argument('--mode',default='720p5000',help='CasparCG channel video mode')
p.add_argument('--sony',action='store_true',help='Also verify native Sony wipes')
p.add_argument('--full-sony',action='store_true',help='Verify Standard, Enhanced and Rotary masks (0.9.0)')
p.add_argument('--expanded-sony',action='store_true',help='Verify the 18 implemented Sony patterns (requires casparMIX 0.7.0)')
p.add_argument('--rendered',action='store_true',help='Also verify isolated rendered compositions')
p.add_argument('--synchronized',action='store_true',help='Use a shared progressive frame clock')
a=p.parse_args()
root=a.output or Path(tempfile.mkdtemp(prefix='casparmix-regression-'))
root.mkdir(parents=True,exist_ok=True)
for name in ('media','log','data','template','cache'):(root/name).mkdir(exist_ok=True)
with socket.socket() as probe:
    probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
config=root/'caspar.config'
config.write_text(f'''<configuration><paths><media-path>{root}/media/</media-path><log-path>{root}/log/</log-path><data-path>{root}/data/</data-path><template-path>{root}/template/</template-path></paths><html><enable-gpu>false</enable-gpu><cache-path>{root}/cache</cache-path></html><ndi><auto-load>false</auto-load></ndi><channels>{('<channel><video-mode>'+a.mode+'</video-mode>'+('<sync-group>test</sync-group>' if a.synchronized else '')+'</channel>')*3}</channels><controllers><tcp><port>{port}</port><protocol>AMCP</protocol></tcp></controllers></configuration>''')
print('ARTIFACTS',root,flush=True)
sony_codes=tuple(range(1,25))+(26,27,29,49)+tuple(range(100,108))+tuple(range(300,305)) if a.full_sony else (1,2,3,4,5,6,7,8,9,10,11,12,17,18,21,22,23,24) if a.expanded_sony else (1,3,5,6,9,17,18,21,23,24)
results={}
with (root/'server.log').open('w') as log:
    proc=subprocess.Popen([str(a.binary.resolve()),str(config)],cwd=root,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT)
    try:
        s=None
        for _ in range(100):
            if proc.poll() is not None:raise RuntimeError('Server exited; see server.log')
            try:s=socket.create_connection(('127.0.0.1',port),.2);break
            except OSError:time.sleep(.2)
        if s is None:raise RuntimeError('AMCP unavailable')
        with s:
            s.settimeout(5);reader=s.makefile('rb')
            transcript=(root/'amcp.log').open('w')
            def cmd(command):
                s.sendall((command+'\r\n').encode());reply=reader.readline().decode().strip()
                transcript.write(command+' -> '+reply+'\n');transcript.flush()
                if not reply.startswith('2'):raise RuntimeError(command+' -> '+reply)
                if reply.startswith('201'):reader.readline()
                elif reply.startswith('200'):
                    while reader.readline().strip():pass
            def record(name, actions, check="constant"):
                path=root/(name+'.mkv')
                cmd(f'ADD 3 FILE "{path}" -codec:v ffv1 -pix_fmt bgra -an')
                time.sleep(.4)
                for command,delay in actions:
                    cmd(command);time.sleep(delay)
                time.sleep(.4);cmd(f'REMOVE 3 FILE "{path}"');time.sleep(.2)
                hashes=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-an','-f','framemd5','-']).decode()
                frames=[line.split(',')[-1].strip() for line in hashes.splitlines() if not line.startswith('#')]
                # Ignore recording startup; the reference is a settled output.
                reference=frames[15]
                pixels=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-an','-vf','scale=8:8:flags=area','-pix_fmt','rgb24','-f','rawvideo','-'])
                width=8*8*3; samples=[pixels[i:i+width] for i in range(0,len(pixels),width)]
                settled=samples[15]
                if check == 'constant':
                    bad=[i for i,frame in enumerate(samples[15:],15) if max(abs(x-y) for x,y in zip(frame,settled))>2]
                else:
                    bad=[i for i,frame in enumerate(samples[15:],15) if any(abs(sum(frame[j:j+3])-255)>4 for j in range(0,width,3))]
                results[name]=dict(frames=len(frames),different_frames=bad,reference=reference)
                return bad
            cmd('PLAY 1-1 #ff0000');cmd('PLAY 2-1 route://1-1');cmd('PLAY 3-1 route://1-1');time.sleep(.5)
            actions=[]
            for _ in range(3):
                for transition in ('MIX','WIPE','PUSH','SLIDE','CUTFADE','VFADE'):
                    actions.append((f'PLAY 3-1 route://2 {transition} 1',.10))
                    actions.append(('PLAY 3-1 route://1-1',.10))
            record('one-frame-and-route-cuts',actions)
            if a.rendered:
                cmd('PLAY 2-1 #ff0000');cmd('PLAY 2-2 #0000ff');cmd('MIXER 2-2 OPACITY 0.5');cmd('MIXER 2-2 FILL 0 0 0.5 0.5')
                cmd('PLAY 3-1 route://2');time.sleep(.5)
                record('rendered-orientation',[("PLAY 3-1 route://2 RENDERED",.3),("PLAY 3-1 route://2",.3)]*3)
                cmd('PLAY 3-1 route://2 RENDERED');time.sleep(.3)
                record('rendered-nested-composition',[("PLAY 3-1 route://2 RENDERED MIX 25",.65)]*5)
                cmd('CLEAR 2-2');cmd('PLAY 2-1 route://1-1');time.sleep(.3)
                record('rendered-and-direct-cuts',[("PLAY 3-1 route://1-1",.12),("PLAY 3-1 route://2 RENDERED",.12)]*10)
            if a.sony:
                cmd('CLEAR 2');cmd('PLAY 2-1 route://1-1');cmd('PLAY 3-1 route://1-1');time.sleep(.3)
                actions=[]
                for code in sony_codes:
                    actions.extend([(f'PLAY 3-1 route://2 RENDERED WIPESONY 1 SONY {code} MANUAL 1 SOFT 25',.08),
                        ('CALL 3-1 "PROGRESS 0.5"',.10),('CALL 3-1 "PROGRESS 1"',.08),('PLAY 3-1 route://1-1',.08)])
                record('native-sony-same-picture',actions)
                cmd('PLAY 2-1 #0000ff');cmd('PLAY 3-1 route://1-1');time.sleep(.3)
                actions=[]
                for code in sony_codes:
                    actions.extend([(f'PLAY 3-1 route://2 RENDERED WIPESONY 1 SONY {code} MANUAL 1 SOFT 25 BORDER 30 BORDERCOLOR #00ff00',.08),
                        ('CALL 3-1 "PROGRESS 0.1"',.05),('CALL 3-1 "PROGRESS 0.5"',.08),
                        ('CALL 3-1 "PROGRESS 0.9"',.05),('CALL 3-1 "PROGRESS 1"',.08),('PLAY 3-1 route://1-1',.08)])
                record('native-sony-soft-border',actions,check='partition')
                actions=[]
                for code in sony_codes:
                    actions.extend([(f'PLAY 3-1 route://2 RENDERED WIPESONY 15 SONY {code} SOFT 25 BORDER 30 BORDERCOLOR #00ff00',.40),
                        ('PLAY 3-1 route://1-1',.08)])
                record('native-sony-timed',actions,check='partition')
                for mode in ('DRAW','GAP'):
                    actions=[]
                    for code in (9,21,23,24):
                        actions.append((f'PLAY 3-1 route://2 RENDERED WIPESONY 1 SONY {code} MANUAL 1 SOFT 25 BORDER 30 BORDERMODE {mode} BORDERCOLOR #00ff00',.08))
                        for progress in (0,.99,.01,.8,.2,.5,1,0):
                            actions.append((f'CALL 3-1 "PROGRESS {progress} SOFT 40 BORDER 40 ASPECT 1.5 MULTI 4 BORDERCOLOR #00ff00"',.02))
                        actions.append(('PLAY 3-1 route://1-1',.08))
                    record('native-sony-fast-live-'+mode.lower(),actions,check='partition')
            if a.sony:
                cmd('PLAY 1-1 #ff0000');cmd('PLAY 2-1 #0000ff')
                for code in (21,23,24):
                    for aspect in (1,2):
                        cmd('PLAY 3-1 route://1-1');time.sleep(.2)
                        cmd(f'PLAY 3-1 route://2 RENDERED WIPESONY 1 SONY {code} MANUAL 1 ASPECT {aspect}')
                        cmd('CALL 3-1 "PROGRESS 0.2"');time.sleep(.2)
                        name=f'iris-{code}-aspect-{aspect}'
                        record(name,[])
                        # Measure the actual full-resolution blue iris, not a normalized UV shape.
                        image=subprocess.check_output(['ffmpeg','-v','error','-i',str(root/(name+'.mkv')),'-vf','select=eq(n\\,20)','-frames:v','1','-pix_fmt','rgb24','-f','rawvideo','-'])
                        if a.mode!='720p5000':continue
                        xs=[];ys=[];aa=0
                        for offset in range(0,len(image),3):
                            red,green,blue=image[offset:offset+3]
                            if blue>200 and red<30:
                                pixel=offset//3;xs.append(pixel%1280);ys.append(pixel//1280)
                            if 2<red<253 and 2<blue<253:aa+=1
                        width=max(xs)-min(xs)+1;height=max(ys)-min(ys)+1
                        ratio=width/height
                        results[name].update(width=width,height=height,ratio=ratio,antialiased_pixels=aa)
                        expected=aspect*(16/9 if a.full_sony and code!=24 else 1)
                        if abs(ratio-expected)>.03 or aa==0:results[name]['different_frames'].append('geometry-or-AA')
            # Routed audio must stay a single mix, including a GPU-only rendered channel.
            tone=root/'media'/'tone.wav'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=1000:sample_rate=48000:duration=20','-ac','2','-y',str(tone)],check=True)
            cmd('CLEAR 1');cmd('CLEAR 2');cmd('CLEAR 3')
            cmd('PLAY 1-1 tone');cmd('PLAY 2-1 route://1-1');cmd('PLAY 3-1 route://2 RENDERED')
            time.sleep(.5)
            audio=root/'rendered-audio.mkv'
            cmd(f'ADD 3 FILE "{audio}" -codec:v ffv1 -pix_fmt bgra -codec:a pcm_s24le')
            time.sleep(1)
            for _ in range(3):
                cmd('PLAY 3-1 route://1-1');time.sleep(.2)
                cmd('PLAY 3-1 route://2 RENDERED MIX 10');time.sleep(.3)
            time.sleep(.3);cmd(f'REMOVE 3 FILE "{audio}"');time.sleep(.2)
            import array,math
            pcm=array.array('f',subprocess.check_output(['ffmpeg','-v','error','-i',str(audio),'-vn','-ac','2','-ar','48000','-f','f32le','-']))
            windows=[]
            for i in range(48000,len(pcm)-9600,9600):
                part=pcm[i:i+9600];windows.append(math.sqrt(sum(x*x for x in part)/len(part)))
            # FFmpeg producer centers a mono sine across the stereo layout. Compare
            # recorded windows to their own settled reference, rather than gain guesses.
            reference=windows[0]
            bad=[i for i,v in enumerate(windows) if reference < .001 or abs(v-reference)>reference*.03]
            results['rendered-audio']=dict(windows=len(windows),rms=windows,different_frames=bad)
            transcript.close()
    finally:
        if proc.poll() is None:
            proc.stdin.write(b'q\n');proc.stdin.flush()
            try:proc.wait(timeout=8)
            except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=8)
(root/'results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2),flush=True)
raise SystemExit(1 if any(r['different_frames'] for r in results.values()) else 0)
