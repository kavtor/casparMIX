#!/usr/bin/env python3
"""Measure direct/rendered route frame alignment on an isolated progressive server.

With --synchronized, frame identity and continuity are required. An FFV1 source encodes its frame
number in sixteen black/white bars; captures preserve those numbers losslessly.
"""
import argparse
import json
from pathlib import Path
import socket
import statistics
import subprocess
import tempfile
import time


def decode(path, crop=None):
    filters = ([crop] if crop else []) + ['scale=16:1:flags=area']
    pixels = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path),
        '-an', '-vf', ','.join(filters), '-pix_fmt', 'gray', '-f', 'rawvideo', '-'])
    ids = []
    for offset in range(15 * 16, len(pixels), 16):
        bars = pixels[offset:offset + 16]
        if len(bars) != 16 or any(32 < value < 223 for value in bars):
            raise RuntimeError(f'Ambiguous frame identifier at capture frame {offset // 16}')
        ids.append(sum((value > 127) << bit for bit, value in enumerate(bars)))
    return ids


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', required=True, type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--synchronized', action='store_true', help='Enable a shared channel synchronization group')
    parser.add_argument('--mode', default='720p5000', help='Progressive channel video mode')
    parser.add_argument('--fps', default='50', help='Counter clip frame rate, matching --mode')
    args = parser.parse_args()
    root = args.output or Path(tempfile.mkdtemp(prefix='casparmix-route-timing-'))
    root.mkdir(parents=True, exist_ok=True)
    for name in ('media', 'log', 'data', 'template', 'cache'):
        (root / name).mkdir(exist_ok=True)
    # Each frame has an unambiguous ID, independent of source/output timestamps.
    encoder = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo',
        '-pix_fmt', 'gray', '-s', '128x72', '-r', args.fps, '-i', '-', '-an',
        '-c:v', 'ffv1', str(root / 'media' / 'counter.mkv')], stdin=subprocess.PIPE)
    try:
        for number in range(1500):
            row = b''.join(bytes([255 if number & (1 << bit) else 0]) * 8 for bit in range(16))
            encoder.stdin.write(row * 72)
        encoder.stdin.close()
        if encoder.wait() != 0:
            raise RuntimeError('Counter clip encoding failed')
    finally:
        if encoder.poll() is None:
            encoder.kill()
            encoder.wait()
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    config = root / 'caspar.config'
    channels = ('<channel><video-mode>' + args.mode + '</video-mode>' + ('<sync-group>test</sync-group>' if args.synchronized else '') + '</channel>') * 4
    config.write_text(f'''<configuration><paths><media-path>{root}/media/</media-path><log-path>{root}/log/</log-path><data-path>{root}/data/</data-path><template-path>{root}/template/</template-path></paths><html><enable-gpu>false</enable-gpu><cache-path>{root}/cache</cache-path></html><ndi><auto-load>false</auto-load></ndi><channels>{channels}</channels><controllers><tcp><port>{port}</port><protocol>AMCP</protocol></tcp></controllers></configuration>''')
    print('ARTIFACTS', root, flush=True)
    results = {}
    with (root / 'server.log').open('w') as log:
        server = subprocess.Popen([str(args.binary.resolve()), str(config)], cwd=root,
            stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT)
        try:
            connection = None
            for _ in range(100):
                if server.poll() is not None:
                    raise RuntimeError('Server exited; see server.log')
                try:
                    connection = socket.create_connection(('127.0.0.1', port), .2)
                    break
                except OSError:
                    time.sleep(.2)
            if connection is None:
                raise RuntimeError('AMCP unavailable')
            with connection, (root / 'amcp.log').open('w') as transcript:
                connection.settimeout(5)
                reader = connection.makefile('rb')
                def command(text, reject=False):
                    connection.sendall((text + '\r\n').encode())
                    reply = reader.readline().decode().strip()
                    transcript.write(text + ' -> ' + reply + '\n')
                    transcript.flush()
                    if reject:
                        if not reply.startswith('4') and not reply.startswith('5'):
                            raise RuntimeError('Expected rejection: ' + text + ' -> ' + reply)
                        return
                    if not reply.startswith('2'):
                        raise RuntimeError(text + ' -> ' + reply)
                    if reply.startswith('201'):
                        reader.readline()
                    elif reply.startswith('200'):
                        while reader.readline().strip():
                            pass
                def start(name):
                    path = root / (name + '.mkv')
                    command(f'ADD 3 FILE "{path}" -codec:v ffv1 -pix_fmt bgra -an')
                    return path
                def stop(path):
                    command(f'REMOVE 3 FILE "{path}"')
                    time.sleep(.3)
                command('PLAY 1-1 counter')
                command('PLAY 2-1 route://1-1')
                command('PLAY 4-1 route://2 RENDERED')
                command('PLAY 3-1 route://1-1')
                command('MIXER 3-1 FILL 0 0 0.5 1')
                command('PLAY 3-2 route://4 RENDERED')
                command('MIXER 3-2 FILL 0.5 0 0.5 1')
                time.sleep(1)
                split = start('simultaneous-routes')
                time.sleep(4)
                stop(split)
                direct = decode(split, 'crop=640:720:0:0')
                rendered = decode(split, 'crop=640:720:640:0')
                offsets = [a - b for a, b in zip(direct, rendered)]
                if len(offsets) < 100 or len(set(direct)) < 100:
                    raise RuntimeError('Insufficient moving-source samples')
                results['simultaneous'] = {'samples': len(offsets),
                    'direct_minus_rendered_frames': dict((str(n), offsets.count(n)) for n in sorted(set(offsets))),
                    'median_delay_frames': statistics.median(offsets),
                    'frame_locked': all(n == 0 for n in offsets)}
                command('CLEAR 3-2')
                command('MIXER 3-1 FILL 0 0 1 1')
                # Warm up with the direct path; also record its steady cadence.
                time.sleep(.5)
                cuts = start('alternating-cuts')
                time.sleep(1)
                for _ in range(8):
                    command('PLAY 3-1 route://4 RENDERED')
                    time.sleep(.35)
                    command('PLAY 3-1 route://1-1')
                    time.sleep(.35)
                time.sleep(.5)
                stop(cuts)
                ids = decode(cuts)
                steps = [b - a for a, b in zip(ids, ids[1:])]
                results['cuts'] = {'samples': len(ids),
                    'step_histogram': dict((str(n), steps.count(n)) for n in sorted(set(steps))),
                    'discontinuities': [{'capture_frame': i + 16, 'previous': ids[i],
                        'current': ids[i + 1], 'step': step}
                        for i, step in enumerate(steps) if step != 1],
                    'continuous': all(n == 1 for n in steps)}
                mixes = start('alternating-mixes')
                time.sleep(.5)
                for _ in range(4):
                    command('PLAY 3-1 route://4 MIX 12 RENDERED')
                    time.sleep(.5)
                    command('PLAY 3-1 route://1-1 MIX 12')
                    time.sleep(.5)
                stop(mixes)
                ids = decode(mixes)
                steps = [b - a for a, b in zip(ids, ids[1:])]
                results['mixes'] = {'samples': len(ids),
                    'step_histogram': {str(n): steps.count(n) for n in sorted(set(steps))},
                    'continuous': all(n == 1 for n in steps)}
                if args.synchronized:
                    # Existing graph is 1 -> 2 -> 3. Reject a feedback loop, then
                    # confirm that rejecting it did not stop the shared clock.
                    command('PLAY 1-2 route://3 RENDERED', reject=True)
                    command('PLAY 2-2 route://1-1 BUFFER 1', reject=True)
                    time.sleep(.2)
                    command('PLAY 2-2 route://2-1 BUFFER 1')
                    command('CLEAR 2-2')
                    command('SET 1 MODE 1080p2500', reject=True)
                    command('INFO 3')
                    results['safety'] = {'cycle_rejected': True, 'buffer_rejected': True,
                        'frame_rate_change_rejected': True, 'local_layer_buffer_preserved': True, 'server_responsive': True}

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
    print(json.dumps(results, indent=2), flush=True)
    if args.synchronized and (not results['simultaneous']['frame_locked'] or not results['cuts']['continuous'] or not results['mixes']['continuous']):
        raise SystemExit('Synchronized routes lost frame identity or CUT continuity')


if __name__ == '__main__':
    main()
