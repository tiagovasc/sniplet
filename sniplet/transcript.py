"""Strict word timings; never estimate word locations from sentence cues."""
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_FILLERS = frozenset({"um", "uh", "erm", "er"})


def normalize(text):
    return text.strip().lower().strip('.,!?;:…\"“”()[]')


@dataclass(frozen=True)
class Word:
    text: str
    start: float
    end: float


def validate(words, duration):
    previous = 0.0
    for w in words:
        if not normalize(w.text) or len(w.text.split()) != 1 or '<' in w.text:
            raise ValueError("Every transcript entry must contain one word, with its own millisecond start/end timings.")
        if not all(math.isfinite(t) for t in (w.start, w.end)) or not 0 <= w.start < w.end <= duration + .001:
            raise ValueError("Invalid word times or transcript exceeds the video duration.")
        if w.start < previous - .001:
            raise ValueError("Word timings must be sorted and must not overlap.")
        previous = w.end
    if not words:
        raise ValueError("Transcript contains no word timings.")
    return words


def load(path, duration):
    path = Path(path)
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == '.json':
        data = json.loads(text)
        if not isinstance(data, dict) or data.get('time_unit', 'seconds') not in ('seconds', 'milliseconds'):
            raise ValueError("JSON needs a words array and time_unit of seconds or milliseconds.")
        divisor = 1000 if data.get('time_unit') == 'milliseconds' else 1
        words = [Word(str(w['word']), float(w['start']) / divisor, float(w['end']) / divisor) for w in data['words']]
    elif path.suffix.lower() in ('.srt', '.vtt'):
        def seconds(t):
            parts = t.replace(',', '.').split(':')
            return sum(float(v) * 60 ** i for i, v in enumerate(reversed(parts)))
        words = []
        for block in re.split(r'\n\s*\n', text.replace('\r\n', '\n').strip()):
            lines = block.splitlines()
            for i, line in enumerate(lines):
                if '-->' not in line:
                    continue
                match = re.fullmatch(r'((?:\d{2}:)?\d{2}:\d{2}[.,]\d{3})\s+-->\s+((?:\d{2}:)?\d{2}:\d{2}[.,]\d{3})(?:\s+.*)?', line.strip())
                if not match:
                    raise ValueError("Subtitle timestamps need millisecond precision (HH:MM:SS.mmm).")
                words.append(Word(' '.join(lines[i + 1:]).strip(), seconds(match[1]), seconds(match[2])))
                break
    else:
        raise ValueError("Use word-level SRT, VTT or JSON; paragraph TXT/Markdown exports are not precise enough.")
    return validate(words, duration)
