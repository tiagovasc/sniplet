import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import tempfile


def run(args):
    result = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode:
        raise RuntimeError(result.stderr[-3000:])
    return result


def fingerprint(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def probe(path):
    info = json.loads(run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)]).stdout)
    video = next((s for s in info['streams'] if s['codec_type'] == 'video'), None)
    if video is None or not any(s['codec_type'] == 'audio' for s in info['streams']):
        raise ValueError('Input needs video and audio streams.')
    n, d = map(float, video['avg_frame_rate'].split('/'))
    fps = n / d if d else 0
    duration = float(info['format']['duration'])
    if not math.isfinite(fps) or fps <= 0 or not math.isfinite(duration) or duration <= 0:
        raise ValueError('Invalid frame rate or duration.')
    if any(x.get('rotation', 0) for x in video.get('side_data_list', [])):
        raise ValueError('Normalize rotation metadata before processing this video.')
    return dict(fps=fps, duration=duration, width=video['width'], height=video['height'])


def silences(path, duration, noise=-34, minimum=.85):
    log = run(['ffmpeg', '-hide_banner', '-i', str(path), '-map', '0:a:0', '-af', f'silencedetect=noise={noise}dB:d={minimum}', '-f', 'null', '-']).stderr
    intervals, start = [], None
    for kind, raw in re.findall(r'silence_(start|end):\s*([\d.]+)', log):
        if kind == 'start':
            start = float(raw)
        elif start is not None:
            intervals.append((max(0, start), min(duration, float(raw))))
            start = None
    if start is not None:
        intervals.append((start, duration))
    return intervals


def render(source, output, cuts, info):
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output or output.exists():
        raise ValueError('Choose a new output path; existing files are never overwritten.')
    if output.suffix.lower() != '.mp4':
        raise ValueError('Output must be an .mp4 file.')
    cursor, spans = 0., []
    for cut in cuts:
        a, b = cut['start'], cut['end']
        if not (math.isfinite(a) and math.isfinite(b) and cursor <= a < b < info['duration']):
            raise ValueError('Invalid, unsorted or overlapping cuts.')
        spans.append((cursor, a))
        cursor = b
    spans.append((cursor, info['duration']))
    filters = []
    for i, (a, b) in enumerate(spans):
        if b <= a:
            raise ValueError('Empty retained segment.')
        filters.append(f'[0:v:0]trim=start={a:.9f}:end={b:.9f},setpts=PTS-STARTPTS[v{i}]')
        audio = f'[0:a:0]atrim=start={a:.9f}:end={b:.9f},asetpts=PTS-STARTPTS'
        if i > 0:
            audio += ',afade=t=in:d=0.004'
        if i < len(spans)-1:
            audio += f',afade=t=out:st={max(0,b-a-.004):.9f}:d=0.004'
        filters.append(audio + f'[a{i}]')
    filters.append(''.join(f'[v{i}][a{i}]' for i in range(len(spans))) + f'concat=n={len(spans)}:v=1:a=1[v][a]')
    with tempfile.TemporaryDirectory(prefix='sniplet-') as temp:
        script = Path(temp) / 'filters.txt'
        script.write_text(';\n'.join(filters), encoding='utf-8')
        run(['ffmpeg', '-hide_banner', '-n', '-i', str(source), '-filter_complex_script', str(script), '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(output)])
    expected = sum(b-a for a,b in spans)
    actual = probe(output)['duration']
    if abs(actual - expected) > max(.15, 2 / info['fps']):
        raise RuntimeError(f'Output timing verification failed: expected {expected:.3f}s, got {actual:.3f}s. Keep for inspection.')
    return dict(expected_duration=expected, output_duration=actual)
