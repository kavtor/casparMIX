#!/usr/bin/env python3
"""Check native enhanced iris bounds and pixel-identical rendered routes."""
import argparse
import json
from pathlib import Path
import socket
import subprocess
import time
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    for name in ('media', 'log', 'data', 'template'):
        (root / name).mkdir(exist_ok=True)
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    config = root / 'caspar.config'
    config.write_text('<configuration><paths>' + ''.join(
        f'<{name}-path>{root}/{name}</{name}-path>'
        for name in ('media', 'log', 'data', 'template')) +
        '</paths><ndi><auto-load>false</auto-load></ndi><channels>' +
        '<channel><video-mode>720p5000</video-mode><sync-group>iris</sync-group></channel>' * 4 +
        f'</channels><controllers><tcp><port>{port}</port><protocol>AMCP</protocol></tcp></controllers></configuration>')
    results = {}
    with (root / 'server.log').open('w') as log:
        process = subprocess.Popen([str(args.binary.resolve()), str(config)],
                                   cwd=root, stdin=subprocess.PIPE, stdout=log, stderr=log)
        try:
            connection = None
            for _ in range(100):
                try:
                    connection = socket.create_connection(('127.0.0.1', port), .2)
                    break
                except OSError:
                    time.sleep(.2)
            if connection is None:
                raise RuntimeError('Isolated server did not start; see server.log')
            connection.settimeout(10)
            reader = connection.makefile('rb')

            def command(text):
                connection.sendall((text + '\r\n').encode())
                reply = reader.readline().decode().strip()
                if not reply.startswith('2'):
                    raise RuntimeError((text, reply))
                return reader.readline().decode().strip() if reply.startswith('201') else ''

            results['version'] = command('VERSION')
            command('PLAY 1-1 #ff0000')
            command('PLAY 2-1 #0000ff')
            time.sleep(.2)
            cases = [(26, 5), (27, 5)] + [(49, n) for n in (3, 4, 5, 6, 7, 8, 64)]
            for code, vertices in cases:
                for center in (.5, .65):
                    name = f'{code}-vertices-{vertices}-y-{center}'
                    command('PLAY 3-1 route://1 RENDERED')
                    time.sleep(.05)
                    command(f'PLAY 3-1 route://2 RENDERED WIPESONY 25 SONY {code} MANUAL 1 VERTICES {vertices}')
                    command(f'CALL 3-1 "PROGRESS .08 X .5 Y {center}"')
                    command('PLAY 4-1 route://3 RENDERED')
                    time.sleep(.15)
                    paths = [root / f'{name}-{ch}.mkv' for ch in (3, 4)]
                    for ch, path in zip((3, 4), paths):
                        command(f'ADD {ch} FILE "{path}" -codec:v ffv1')
                    time.sleep(.45)
                    for ch, path in zip((3, 4), paths):
                        command(f'REMOVE {ch} FILE "{path}"')
                    time.sleep(.15)
                    frames = [subprocess.check_output([
                        'ffmpeg', '-v', 'error', '-i', str(path), '-vf', 'select=eq(n\\,8)',
                        '-frames:v', '1', '-pix_fmt', 'rgb24', '-f', 'rawvideo', '-']) for path in paths]
                    assert frames[0] == frames[1], f'{name}: rendered route differs'
                    pixels = np.frombuffer(frames[0], dtype=np.uint8).reshape(720, 1280, 3)
                    mask = (pixels[:, :, 2] > 220) & (pixels[:, :, 0] < 30)
                    ys, xs = np.where(mask)
                    assert len(ys) > 100, f'{name}: empty iris'
                    # Pixel centres live at (index + .5) / height.
                    measured_center = (int(ys.min()) + int(ys.max()) + 1) / 2
                    error = measured_center - center * 720
                    assert abs(error) <= 2, (name, error)
                    assert ys.min() > 0 and ys.max() < 719, f'{name}: clipped test shape'
                    results[name] = dict(bounds=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
                                         vertical_center_error_px=error, rendered_route_identical=True)
                    print('VERIFIED', name, 'center error px', error, flush=True)
        finally:
            process.stdin.write(b'q\n')
            process.stdin.flush()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=8)
    (root / 'results.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
