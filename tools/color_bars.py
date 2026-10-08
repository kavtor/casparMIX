#!/usr/bin/env python3
"""Capture native color bars and compare with the matching FFmpeg reference."""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import tempfile
import time

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--binary', required=True, type=Path)
p.add_argument('--output', type=Path)
p.add_argument('--width', type=int, default=1280)
p.add_argument('--height', type=int, default=720)
a = p.parse_args()
if not 320 <= a.width <= 3840 or not 240 <= a.height <= 2160: p.error('Invalid raster dimensions')
root = a.output or Path(tempfile.mkdtemp(prefix='casparmix-colorbars-'))
root.mkdir(parents=True, exist_ok=True)
for name in ('media','log','data','template','cache'): (root/name).mkdir(exist_ok=True)
with socket.socket() as probe:
    probe.bind(('127.0.0.1',0)); port=probe.getsockname()[1]
config=root/'caspar.config'
config.write_text(f'<configuration><paths><media-path>{root}/media/</media-path><log-path>{root}/log/</log-path><data-path>{root}/data/</data-path><template-path>{root}/template/</template-path></paths><ndi><auto-load>false</auto-load></ndi><video-modes><video-mode><id>BAR_TEST</id><width>{a.width}</width><height>{a.height}</height><field-count>1</field-count><time-scale>50</time-scale><duration>1</duration></video-mode></video-modes><channels><channel><video-mode>BAR_TEST</video-mode><sync-group>test</sync-group></channel></channels><controllers><tcp><port>{port}</port><protocol>AMCP</protocol></tcp></controllers></configuration>')
report={}
with (root/'server.log').open('w') as log:
    proc=subprocess.Popen([str(a.binary.resolve()),str(config)],cwd=root,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT)
    try:
        s=None
        for _ in range(100):
            if proc.poll() is not None: raise RuntimeError('Server exited; see server.log')
            try: s=socket.create_connection(('127.0.0.1',port),.2); break
            except OSError: time.sleep(.2)
        if s is None: raise RuntimeError('AMCP unavailable')
        with s,(root/'amcp.log').open('w') as transcript:
            s.settimeout(5);reader=s.makefile('rb')
            def command(text, reject=False):
                s.sendall((text+'\r\n').encode());reply=reader.readline().decode().strip()
                transcript.write(text+' -> '+reply+'\n');transcript.flush()
                if reject:
                    if not reply.startswith(('4','5')): raise RuntimeError('Expected rejection: '+reply)
                elif not reply.startswith('2'): raise RuntimeError(text+' -> '+reply)
            for key,source,matrix in [('EBU75','pal75bars','bt601'),('EBU100','pal100bars','bt601'),('SMPTESD','smptebars','bt601'),('SMPTEHD','smptehdbars','bt709')]:
                command('PLAY 1-1 COLORBARS '+key);time.sleep(.3)
                path=root/(key+'.mkv')
                command(f'ADD 1 FILE "{path}" -codec:v ffv1 -pix_fmt bgra -an');time.sleep(.9)
                command(f'REMOVE 1 FILE "{path}"');time.sleep(.25)
                image=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vf','select=eq(n\\,15)','-frames:v','1','-pix_fmt','bgra','-f','rawvideo','-'])
                reference=subprocess.check_output(['ffmpeg','-v','error','-f','lavfi','-i',source+f'=size={a.width}x{a.height}:rate=1,format=pix_fmts=yuv444p,scale=in_color_matrix='+matrix+':in_range=tv:out_range=pc,format=pix_fmts=bgra','-frames:v','1','-f','rawvideo','-'])
                if len(image)!=len(reference): raise RuntimeError('Capture/reference size mismatch')
                error=sum(abs(x-y) for x,y in zip(image,reference))/len(image)
                hashes=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-an','-f','framemd5','-']).decode()
                frames=[line.split(',')[-1].strip() for line in hashes.splitlines() if not line.startswith('#')][15:]
                if not frames or len(set(frames))!=1: raise RuntimeError(key+' is not static')
                if error>2: raise RuntimeError(key+' differs from reference: '+str(error))
                row=image[(a.height//4)*a.width*4:(a.height//4+1)*a.width*4]
                colors=len(set(row[i:i+4] for i in range(0,len(row),4)))
                if colors>16: raise RuntimeError(key+' has interpolated bar interiors')
                report[key]={'settled_frames':len(frames),'mean_absolute_bgra_error':error,'top_row_colors':colors,'static':True,'sha256':hashlib.sha256(image).hexdigest()}
            command('PLAY 1-1 COLORBARS INVALID',reject=True)
            report['invalid_pattern_rejected']=True
    finally:
        if proc.poll() is None:
            proc.stdin.write(b'q\n');proc.stdin.flush()
            try: proc.wait(timeout=8)
            except subprocess.TimeoutExpired: proc.terminate();proc.wait(timeout=8)
(root/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
