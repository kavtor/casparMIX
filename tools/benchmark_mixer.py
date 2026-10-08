"""Measure synchronized mixer cadence with moving inputs, nested M/Es and native MV.

This isolated composition benchmark does not certify encoding/output consumers or
arbitrary hardware. Run at 60 and 75 fps to establish a concrete capacity margin.
"""
import argparse
import base64
import csv
import io
import json
import math
import socket
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fps', type=int, choices=(60, 75, 100, 120, 130, 140, 150, 200), default=60)
    parser.add_argument('--auto-progress', action='store_true', help='Animate effects on every output frame with native timed progress')
    parser.add_argument('--sony', type=int, choices=(1201, 1355, 1356, 1357, 1358), default=1355, help='Native foreground DME to stress')
    parser.add_argument('--seconds', type=float, default=20)
    parser.add_argument('--clip', type=Path, required=True, help='1080p60 moving test clip, at least 6 seconds')
    parser.add_argument('--ndi-probe', type=Path, help='Enable PGM and MV NDI consumers and receive them with strata-ndi-timing')
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or args.seconds < 5:
        parser.error('--seconds must be finite and at least 5')
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    for name in ('media', 'template', 'log', 'data'):
        (root / name).mkdir(exist_ok=True)
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1', 0))
        port = reservation.getsockname()[1]
    # All 110 reserved channels share one progressive clock; most stay idle.
    mode = ('<video-modes><video-mode><id>bench</id><width>1920</width>'
            '<height>1080</height><time-scale>%d</time-scale><duration>1</duration>'
            '</video-mode></video-modes>') % args.fps
    channels = '<channel><sync-group>bench</sync-group><video-mode>bench</video-mode></channel>' * 110
    config = root / 'caspar.config'
    config.write_text('<configuration><paths>' + ''.join(
        f'<{name}-path>{root / name}</{name}-path>' for name in ('media', 'template', 'log', 'data'))
        + '</paths><ndi><auto-load>false</auto-load></ndi>' + mode
        + '<channels>' + channels + '</channels><controllers><tcp><port>'
        + str(port) + '</port><protocol>AMCP</protocol></tcp></controllers></configuration>')
    samples = []
    probes = []
    try:
        with socket.create_connection(('127.0.0.1', 5250), .2):
            background_renderer = True
    except OSError:
        background_renderer = False
    with (root / 'server.log').open('w') as log:
        proc = subprocess.Popen([str(args.binary.resolve()), str(config)], cwd=root,
                                stdin=subprocess.PIPE, stdout=log, stderr=log)
        connection = None
        try:
            for _ in range(100):
                if proc.poll() is not None:
                    raise RuntimeError('Benchmark server exited during startup')
                try:
                    connection = socket.create_connection(('127.0.0.1', port), .3)
                    break
                except OSError:
                    time.sleep(.2)
            if connection is None:
                raise RuntimeError('Benchmark server did not start')
            connection.settimeout(10)
            reader = connection.makefile('rb')
            transcript = []

            def command(text):
                connection.sendall((text + '\r\n').encode())
                status = reader.readline().decode().strip()
                transcript.append([text, status])
                if not status.startswith('2'):
                    raise RuntimeError((text, status))
                if text.startswith('INFO '):
                    lines = []
                    while True:
                        line = reader.readline()
                        if line in (b'\r\n', b'\n', b''):
                            break
                        lines.append(line)
                    return ET.fromstring(b''.join(lines))
                if status.startswith('201'):
                    return reader.readline().decode().strip()

            version = command('VERSION')
            clip = str(args.clip.resolve()).replace('"', '\\"')
            for ch in range(1, 7):
                command(f'PLAY {ch}-1 "{clip}" LOOP')
            command('PLAY 7-1 #777777')
            command('PLAY 8-1 #112233')
            for dest, source in ((17, 3), (18, 4), (15, 1), (16, 2), (13, 17), (14, 6), (10, 13), (9, 7)):
                command(f'PLAY {dest}-1 route://{source} RENDERED')
            duration = math.ceil((args.seconds + 20) * args.fps) if args.auto_progress else 60
            manual = 0 if args.auto_progress else 1
            command(f'PLAY 13-1 route://5 RENDERED WIPESONY {duration} SONY 24 MANUAL {manual} SOFT 12 BORDER 15')
            if not args.auto_progress:
                command('CALL 13-1 "PROGRESS 0.5"')
            command(f'PLAY 10-1 route://15 RENDERED DMENATIVE {duration} SONY_{args.sony} MANUAL {manual}')
            if not args.auto_progress:
                command('CALL 10-1 "PROGRESS 0.5"')
            tiles = list(range(1, 9)) + [10, 13, 15, 17]
            for layer, source in enumerate(tiles, 1):
                command(f'PLAY 11-{layer} route://{source} RENDERED')
                command(f'MIXER 11-{layer} FILL {(layer-1)%4/4} {(layer-1)//4/3} .25 {1/3}')
            command('PLAY 11-80 GRAPHICS')
            scene = {'width': 1920, 'height': 1080, 'nodes': []}
            for tile in range(12):
                scene['nodes'].append({'type': 'text', 'x': tile % 4 * 480 + 10,
                    'y': tile // 4 * 360 + 330, 'w': 300, 'h': 26, 'text': f'{tile+1} - BENCHMARK',
                    'size': 20, 'color': '#ffffff'})
            scene['nodes'].append({'type': 'clock', 'x': 1300, 'y': 5, 'w': 300, 'h': 40, 'size': 28, 'color': '#ffffff'})
            payload = base64.b64encode(json.dumps(scene).encode()).decode()
            command(f'CALL 11-80 SCENE {payload}')
            if args.ndi_probe:
                token = f'CASPARMIX_BENCH_{port}'
                for ch in (10, 11):
                    command(f'ADD {ch} NDI NAME {token}_{ch}')
                listed = subprocess.check_output([str(args.ndi_probe.resolve()), '--list'], text=True).splitlines()
                for ch in (10, 11):
                    matches = [name for name in listed if token + '_' + str(ch) in name]
                    if len(matches) != 1:
                        raise RuntimeError(('NDI source discovery failed', ch, matches))
                    probe = subprocess.Popen([str(args.ndi_probe.resolve()), '--source', matches[0],
                        '--seconds', str(math.ceil(args.seconds))], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    probes.append((ch, probe))
            time.sleep(3)  # Exclude decoder, graphics and receiver startup.
            start = time.monotonic()
            while time.monotonic() - start <= args.seconds:
                before = time.monotonic()
                info = command('INFO 1')
                wall = time.monotonic()
                times = [float(value.text) for value in info.findall('.//time')]
                timing = {}
                for ch in (10, 11, 13):
                    values = command(f'INFO {ch}').find('performance')
                    timing[str(ch)] = {node.tag: float(node.text) for node in values} if values is not None else {}
                samples.append({'wall': wall, 'epoch': int(info.findtext('.//frame-sync/epoch')),
                                'media_times': times, 'timing_ms': timing})
                progress = .05 + .9 * (.5 + .5 * math.sin((wall-start)*1.7))
                if not args.auto_progress:
                    command(f'CALL 13-1 "PROGRESS {progress}"')
                    command(f'CALL 10-1 "PROGRESS {progress}"')
                time.sleep(max(0, .2 - (time.monotonic()-before)))
            elapsed = samples[-1]['wall'] - samples[0]['wall']
            fps = (samples[-1]['epoch'] - samples[0]['epoch']) / elapsed
            windows = []
            for i in range(5, len(samples)):
                a, b = samples[i-5], samples[i]
                windows.append((b['epoch']-a['epoch'])/(b['wall']-a['wall']))
            windows.sort()
            media_advance = 0.
            for a, b in zip(samples, samples[1:]):
                if len(a['media_times']) < 2 or len(b['media_times']) < 2:
                    raise RuntimeError('Moving input did not expose its elapsed/duration clock')
                step = b['media_times'][0] - a['media_times'][0]
                if step < 0:
                    step += a['media_times'][1]  # Unwrap fixture LOOP, not a playback seek.
                media_advance += step
            native_rate = media_advance / elapsed
            deliveries = {}
            for ch, probe in probes:
                output, errors = probe.communicate(timeout=10)
                (root / f'ndi-{ch}.csv').write_text(output)
                if probe.returncode:
                    raise RuntimeError(('NDI receive probe failed', ch, errors))
                rows = list(csv.DictReader(io.StringIO(output)))
                stable = rows[2:]  # Receiver connection startup is not steady delivery.
                if len(stable) < 3:
                    raise RuntimeError(('NDI receive probe too short', ch))
                a, b = stable[0], stable[-1]
                delivered = (int(b['video_frames']) - int(a['video_frames'])) / (float(b['elapsed_s']) - float(a['elapsed_s']))
                deliveries[str(ch)] = {'measured_fps': delivered,
                    'min_one_second_fps': min(float(row['video_hz']) for row in stable),
                    'video_timecode_gaps_after_startup': int(b['video_tc_gaps']) - int(a['video_tc_gaps']),
                    'sdk_video_dropped_after_startup': int(b['sdk_video_dropped']) - int(a['sdk_video_dropped']),
                    'sdk_audio_dropped_after_startup': int(b['sdk_audio_dropped']) - int(a['sdk_audio_dropped']),
                    'scope': 'Local NDI receiver delivery; timecodes do not prove content lip-sync.'}
            result = {'version': version, 'target_fps': args.fps, 'measured_fps': fps,
                'one_second_window_min_fps': min(windows),
                'one_second_window_p05_fps': windows[int((len(windows)-1)*.05)],
                'duration_seconds': elapsed, 'sample_count': len(samples),
                'media_seconds_per_wall_second': native_rate, 'ndi_delivery': deliveries,
                'configuration': {'raster': '1920x1080', 'moving_inputs': 6, 'static_inputs': 2,
                    'me_pairs': 4, 'nested_wipe_and_dme': True, 'foreground_sony_dme': args.sony, 'effect_progress': 'native-every-frame' if args.auto_progress else 'manual-5hz', 'native_mv_tiles': 12,
                    'native_mv_labels': True, 'reserved_channels': 110, 'output_consumers': len(probes)},
                'background_renderer_port_5250_open_at_start': background_renderer,
                'scope': 'Defined workload with desktop/other processes present; original renderer availability is recorded separately. Consumers only validated when ndi_delivery is present. No arbitrary-hardware/encoder guarantee.',
                'composition_clock_window_pass': min(windows) >= args.fps * .97,
                # With real receivers, output cadence is measured at delivery.
                # Producer epochs can catch up behind the consumer buffer.
                'cadence_pass': fps >= args.fps * .995 and (bool(deliveries) or min(windows) >= args.fps * .97)
                    and .995 <= native_rate <= 1.005
                    and all(v['measured_fps'] >= args.fps * .995 and v['min_one_second_fps'] >= args.fps * .97 and v['sdk_video_dropped_after_startup'] == 0 and v['sdk_audio_dropped_after_startup'] == 0 for v in deliveries.values()),
                'samples': samples}
            (root / 'transcript.json').write_text(json.dumps(transcript, indent=2))
            (root / 'results.json').write_text(json.dumps(result, indent=2))
            print(json.dumps({k: v for k, v in result.items() if k != 'samples'}), flush=True)
            if not result['cadence_pass']:
                raise RuntimeError('Composition missed its cadence target; inspect results.json')
        finally:
            for _, probe in probes:
                if probe.poll() is None:
                    probe.terminate()
                    probe.wait(timeout=10)
            if connection is not None:
                connection.close()
            if proc.poll() is None:
                proc.stdin.write(b'q\n')
                proc.stdin.flush()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.terminate()
                    proc.wait(timeout=10)


if __name__ == '__main__':
    main()
