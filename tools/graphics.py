#!/usr/bin/env python3
"""Validate native graphics scenes with isolated lossless engine captures."""
import argparse
import base64
import json
from pathlib import Path
import socket
import subprocess
import tempfile
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--binary', required=True, type=Path)
parser.add_argument('--output', type=Path)
parser.add_argument('--scene', type=Path, help='Optional client scene for an additional visual capture')
args = parser.parse_args()
root = args.output or Path(tempfile.mkdtemp(prefix='casparmix-graphics-'))
root.mkdir(parents=True, exist_ok=True)
for name in ('media', 'log', 'data', 'template', 'cache'):
    (root / name).mkdir(exist_ok=True)
with socket.socket() as probe:
    probe.bind(('127.0.0.1', 0))
    port = probe.getsockname()[1]
width, height = (2304, 1080) if args.scene else (640, 360)
config = root / 'caspar.config'
config.write_text(f'''<configuration><paths><media-path>{root}/media</media-path><log-path>{root}/log</log-path><data-path>{root}/data</data-path><template-path>{root}/template</template-path></paths><html><cache-path>{root}/cache</cache-path></html><ndi><auto-load>false</auto-load></ndi><video-modes><video-mode><id>GRAPHICS_TEST</id><width>{width}</width><height>{height}</height><field-count>1</field-count><time-scale>50</time-scale><duration>1</duration></video-mode></video-modes><channels><channel><video-mode>GRAPHICS_TEST</video-mode><sync-group>graphics-test</sync-group></channel></channels><controllers><tcp><port>{port}</port><protocol>AMCP</protocol></tcp></controllers></configuration>''')
results = {}
with (root / 'server.log').open('w') as log:
    server = subprocess.Popen([str(args.binary.resolve()), str(config)], cwd=root,
                              stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT)
    try:
        connection = None
        for _ in range(100):
            if server.poll() is not None:
                raise RuntimeError('Engine exited; see server.log')
            try:
                connection = socket.create_connection(('127.0.0.1', port), .2)
                break
            except OSError:
                time.sleep(.2)
        if connection is None:
            raise RuntimeError('AMCP did not start')
        connection.settimeout(10)
        reader = connection.makefile('rb')
        with (root / 'amcp.log').open('w') as transcript:
            def command(value, reject=False):
                connection.sendall((value + '\r\n').encode())
                reply = reader.readline().decode().strip()
                transcript.write(value[:160] + ' -> ' + reply + '\n')
                transcript.flush()
                if reject:
                    assert reply.startswith(('4', '5')), reply
                else:
                    assert reply.startswith('2'), reply
                if reply.startswith('201'):
                    reader.readline()

            def update(value, kind='SCENE', reject=False):
                encoded = base64.b64encode(json.dumps(value, separators=(',', ':')).encode()).decode()
                command('CALL 1-80 ' + kind + ' ' + encoded, reject)

            def capture(name):
                path = root / (name + '.mkv')
                command(f'ADD 1 FILE "{path}" -codec:v ffv1 -an')
                time.sleep(1.4)
                command(f'REMOVE 1 FILE "{path}"')
                time.sleep(1.0)
                pixels = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-vf',
                    'select=eq(n\\,15)', '-frames:v', '1', '-pix_fmt', 'bgra', '-f', 'rawvideo', '-'])
                assert len(pixels) == width * height * 4
                subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(path), '-vf',
                    'select=eq(n\\,15)', '-frames:v', '1', str(root / (name + '.png'))], check=True)
                return pixels

            command('PLAY 1-1 #384450')
            command('PLAY 1-80 GRAPHICS')
            time.sleep(.8)  # A producer must tolerate the gap before its first SCENE.
            capture('before-scene')
            results['empty_startup'] = True
            nodes = [dict(type='text', x=20, y=20, w=500, h=40, size=24, text='NATIVE GRAPHICS',
                          color='#ffffff', bold=True, background='#c01818')]
            for index, (low, high, color) in enumerate(((0, .7, '#1f9d3a'), (.7, .85, '#e2b31a'), (.85, 1, '#d02323'))):
                nodes.append(dict(type='bar', id='band' + str(index), group='meter', x=60,
                                  y=100 + 200 * (1-high), w=12, h=200 * (high-low), minimum=low,
                                  maximum=high, vertical=True, value=.95, color=color, hideOnLost=True))
            nodes.append(dict(type='rect', x=0, y=0, w=640, h=360, color='#ff0000', lostOnly=True))
            scene = dict(width=640, height=360, timeout=10, nodes=nodes)
            update(scene)
            initial = capture('scene')
            update({'band0': .8, 'band1': .8, 'band2': .8}, 'VALUES')
            time.sleep(.5)
            changed = capture('meter-release')
            assert initial != changed
            # Green section remains filled when the yellow section is on.
            def pixel(data, x, y):
                x, y = round(x * width / 640), round(y * height / 360)
                return data[(y * width + x)*4:(y * width + x)*4+4]
            assert pixel(changed, 65, 200)[1] > 120
            update({'unknown': .5}, 'VALUES', reject=True)
            update(dict(scene, width=0), reject=True)
            update(dict(scene, nodes=[dict(nodes[0], color='invalid')]), reject=True)
            stable = capture('after-rejection')
            assert pixel(stable, 65, 200) == pixel(changed, 65, 200)
            results.update(scene_accepted=True, meter_updates=True, green_below_yellow=True,
                           invalid_values_rejected=True, invalid_scene_preserves_previous=True)
            scene['timeout'] = .5
            update(scene)
            time.sleep(.7)
            lost = capture('watchdog')
            assert pixel(lost, 320, 180)[2] > 200
            command('CALL 1-80 HEARTBEAT')
            scene['timeout'] = 10
            update(scene)
            recovered = capture('recovered')
            assert pixel(recovered, 320, 180)[2] < 150
            results.update(watchdog=True, heartbeat_recovery=True)
            centered_nodes = [dict(type='text', x=40, y=40+index*80, w=500, h=42,
                                   size=18, text=label, color='#ffffff', bold=True,
                                   align='center', valign='center')
                              for index,label in enumerate(('NO SOURCE','1 - Camera A','2 - gyjp'))]
            update(dict(width=640,height=360,timeout=10,nodes=centered_nodes))
            centered = capture('ink-centered-text')
            centers=[]
            for node in centered_nodes:
                rows=[]
                for y in range(node['y'],node['y']+node['h']):
                    if any(min(pixel(centered,x,y)[:3])>180 for x in range(40,540)):
                        rows.append(y)
                assert rows, node['text']
                actual=(min(rows)+max(rows))/2
                expected=node['y']+(node['h']-1)/2
                assert abs(actual-expected)<=1,(node['text'],actual,expected)
                centers.append({'text':node['text'],'actual':actual,'expected':expected})
            results['ink_centered_text']=centers
            update(dict(width=640,height=360,timeout=10,nodes=[dict(centered_nodes[0],valign='invalid')]),reject=True)
            if args.scene:
                update(json.loads(args.scene.read_text()))
                capture('client-scene')
                results['client_scene_capture'] = True
    finally:
        if server.poll() is None:
            server.stdin.write(b'q\n')
            server.stdin.flush()
            try:
                server.wait(timeout=8)
            except subprocess.TimeoutExpired:
                server.terminate()
                server.wait(timeout=8)
(root / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps(results, indent=2))
