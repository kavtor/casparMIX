#!/usr/bin/env python3
"""Measure content A/V alignment through repeated native transitions using correlated flash/beep cues."""
import argparse,json,socket,subprocess,time
from pathlib import Path
import numpy as np


def measure(path, fps):
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=codec_type,sample_rate:frame=media_type,best_effort_timestamp_time,nb_samples','-of','json',str(path)]))
    video_pts=np.array([float(f['best_effort_timestamp_time']) for f in info['frames'] if f['media_type']=='video'])
    audio_frames=[f for f in info['frames'] if f['media_type']=='audio']
    rate=int(next(st['sample_rate'] for st in info['streams'] if st['codec_type']=='audio'))
    video=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vf','scale=1:1','-fps_mode','passthrough','-pix_fmt','gray','-f','rawvideo','-'])
    audio=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vn','-map','0:a:0','-ac','1','-f','f32le','-'])
    v=np.frombuffer(video,dtype=np.uint8)>120
    a=np.abs(np.frombuffer(audio,dtype=np.float32))>.1
    if len(v)!=len(video_pts):raise RuntimeError('Decoded video and timestamp counts differ')
    counts=np.array([int(f['nb_samples']) for f in audio_frames]);ends=np.cumsum(counts)
    if len(a)!=ends[-1]:raise RuntimeError('Decoded audio and timestamp counts differ')
    vi=video_pts[np.flatnonzero(v & ~np.r_[False,v[:-1]])]
    indices=np.flatnonzero(a & ~np.r_[False,a[:-1]])
    frame_indices=np.searchsorted(ends,indices,side='right')
    starts=np.r_[0,ends[:-1]]
    audio_pts=np.array([float(f['best_effort_timestamp_time']) for f in audio_frames])
    ai=audio_pts[frame_indices]+(indices-starts[frame_indices])/rate
    ai=ai[np.r_[True,np.diff(ai)>.1]]
    pairs=[]
    for stamp in vi:
        if len(ai):
            sound=float(ai[np.argmin(abs(ai-stamp))])
            if abs(sound-stamp)<.4:pairs.append({'video_s':float(stamp),'audio_s':sound,'offset_ms':1000*(sound-stamp)})
    if len(pairs)<5:raise RuntimeError(f'Too few paired markers in {path}: {len(pairs)}')
    offsets=[p['offset_ms'] for p in pairs]
    slope=float(np.polyfit([p['video_s'] for p in pairs],offsets,1)[0])
    gaps=int(np.count_nonzero(np.diff(video_pts)>1.5/fps))
    return {'pairs':pairs,'min_offset_ms':min(offsets),'max_offset_ms':max(offsets),'drift_ms_per_second':slope,'video_timestamp_gaps':gaps}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seconds',type=int,default=30);p.add_argument('--ndi-probe',type=Path);p.add_argument('--stalls',action='store_true');p.add_argument('--input-fps',default='50');p.add_argument('--input-sample-rate',type=int,default=48000);p.add_argument('--size',default='320x180');args=p.parse_args()
    if args.seconds<10:p.error('Use at least ten seconds')
    root=args.output.resolve();root.mkdir(parents=True,exist_ok=True)
    for d in ['media','data','log','template']:(root/d).mkdir(exist_ok=True)
    clip=root/'cue.mkv'
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i',f"nullsrc=s={args.size}:r={args.input_fps},geq=lum='if(lt(mod(T,1),0.08),235,16)':cb=128:cr=128",'-f','lavfi','-i',r"aevalsrc=if(lt(mod(t\,1)\,0.08)\,0.5*sin(2*PI*1000*t)\,0):s="+str(args.input_sample_rate),'-t',str(args.seconds+10),'-c:v','ffv1','-c:a','pcm_s16le',str(clip)],check=True)
    from fractions import Fraction
    input_result=measure(clip,float(Fraction(args.input_fps)))
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    width,height=map(int,args.size.split('x'))
    mode=f'<video-modes><video-mode><id>av-test</id><width>{width}</width><height>{height}</height><time-scale>50</time-scale><duration>1</duration></video-mode></video-modes>'
    channels=''.join('<channel><sync-group>av-test</sync-group><video-mode>av-test</video-mode></channel>' for _ in range(3))
    config=root/'caspar.config';config.write_text('<configuration><paths>'+''.join(f'<{d}-path>{root}/{d}</{d}-path>' for d in ['media','data','log','template'])+'</paths><ndi><auto-load>false</auto-load></ndi>'+mode+'<channels>'+channels+f'</channels><controllers><tcp><port>{port}</port><protocol>AMCP</protocol></tcp></controllers></configuration>')
    with (root/'server.log').open('w') as log:
        proc=subprocess.Popen([str(args.binary.resolve()),str(config)],cwd=root,stdin=subprocess.PIPE,stdout=log,stderr=log)
        try:
            deadline=time.monotonic()+25
            while True:
                try:s=socket.create_connection(('127.0.0.1',port),.3);break
                except OSError:
                    if proc.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Engine did not become ready; see server.log')
                    time.sleep(.2)
            s.settimeout(10);f=s.makefile('rb')
            def cmd(c):
                s.sendall((c+'\r\n').encode());reply=f.readline().decode().strip()
                if not reply.startswith('2'):raise RuntimeError((c,reply))
                return f.readline().decode().strip() if reply.startswith('201') else ''
            version=cmd('VERSION');cmd(f'PLAY 1-1 "{clip}" LOOP');time.sleep(.4)
            cmd('PLAY 2-1 route://1 RENDERED');cmd('PLAY 3-1 route://1 RENDERED');time.sleep(.4)
            capture=root/'program.mkv';cmd(f'ADD 3 FILE "{capture}" -codec:v ffv1 -filter:v scale=320:180 -codec:a pcm_s16le')
            ndi_proc=None
            if args.ndi_probe:
                ndi_name=f'CASPARMIX_AV_VERIFY_{port}'
                cmd(f'ADD 3 NDI NAME {ndi_name}')
                ndi_log=(root/'ndi-events.csv').open('w')
                ndi_proc=subprocess.Popen([str(args.ndi_probe.resolve()),ndi_name,str(args.seconds)],stdout=ndi_log)
            start=time.monotonic();takes=[];target=2
            while time.monotonic()-start<args.seconds:
                # Equivalent source through two paths isolates handoff/route/transition drift.
                effect=('MIX 10','WIPESONY 10 SONY 23 SOFT 20 BORDER 5','DMENATIVE 10 SONY_1041')[len(takes)%3]
                cmd(f'PLAY 3-1 route://{target} RENDERED {effect}')
                takes.append({'elapsed_s':time.monotonic()-start,'effect':effect,'source':target});target=3-target
                if args.stalls and len(takes)%8==0:
                    import os,signal
                    os.kill(proc.pid,signal.SIGSTOP)
                    try:time.sleep(.15)
                    finally:os.kill(proc.pid,signal.SIGCONT)
                time.sleep(.6)
            cmd(f'REMOVE 3 FILE "{capture}"');time.sleep(.4)
            if ndi_proc:
                ndi_proc.wait(timeout=25);ndi_log.close();cmd('REMOVE 3 NDI')
                if ndi_proc.returncode:raise RuntimeError('NDI content probe failed')
        finally:
            if proc.poll() is None:
                import os,signal
                os.kill(proc.pid,signal.SIGCONT)
                proc.stdin.write(b'q\n');proc.stdin.flush()
                try:proc.wait(timeout=8)
                except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=8)
    output_result=measure(capture,50)
    result={'fixture':{'input_fps':args.input_fps,'input_sample_rate':args.input_sample_rate,'size':args.size,'stalls':args.stalls},'version':version,'method':'Content flash/beep correlation; FILE output, not NDI','input':input_result,'program':output_result,'takes':takes}
    if args.ndi_probe:
        import csv
        rows=list(csv.DictReader((root/'ndi-events.csv').open()))
        video_times=[float(r['timecode_s']) for r in rows if r['kind']=='video']
        audio_times=np.array([float(r['timecode_s']) for r in rows if r['kind']=='audio'])
        pairs=[]
        for stamp in video_times:
            if len(audio_times):
                sound=float(audio_times[np.argmin(abs(audio_times-stamp))])
                if abs(sound-stamp)<.4:pairs.append({'video_s':stamp,'audio_s':sound,'offset_ms':1000*(sound-stamp)})
        if len(pairs)<5:raise RuntimeError('Too few NDI paired markers')
        offsets=[pair['offset_ms'] for pair in pairs];t0=pairs[0]['video_s']
        result['ndi']={'pairs':pairs,'min_offset_ms':min(offsets),'max_offset_ms':max(offsets),'drift_ms_per_second':float(np.polyfit([pair['video_s']-t0 for pair in pairs],offsets,1)[0])}
        print('NDI',json.dumps({k:v for k,v in result['ndi'].items() if k!='pairs'}))
        result['ndi']['within_tolerance']=abs(result['ndi']['drift_ms_per_second']-input_result['drift_ms_per_second'])<=1 and max(offsets)-min(offsets)<=80
    (root/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'input':{k:v for k,v in input_result.items() if k!='pairs'},'program':{k:v for k,v in output_result.items() if k!='pairs'},'transitions':len(takes)},indent=2))
    if output_result['video_timestamp_gaps']:
        raise SystemExit('Recording has timestamp gaps: cannot qualify this capture')
    if abs(output_result['drift_ms_per_second']-input_result['drift_ms_per_second'])>1 or output_result['max_offset_ms']-output_result['min_offset_ms']>80:
        raise SystemExit('A/V content drift exceeds tolerance')
    if args.ndi_probe and not result['ndi']['within_tolerance']:
        raise SystemExit('NDI content drift exceeds tolerance')

if __name__=='__main__':main()
