"""Candidate planning independent of video models."""
import math
from .transcript import DEFAULT_FILLERS, normalize


def candidates(start, end, fps, keep_gap=.5, words=None, fillers=DEFAULT_FILLERS, adjacency=.15):
    """Keep real silence, including when expanding across a neighboring filler."""
    options = [(start + keep_gap / 2, end - keep_gap / 2, 'silence')]
    if words:
        # Only contiguous filler chains at one edge. Never cross a meaningful word.
        trailing = [w for w in words if w.end > end]
        edge = end
        for w in trailing:
            if w.start < end - .04 or w.start - edge > adjacency or normalize(w.text) not in fillers or w.end - end > 2:
                break
            edge = w.end
            options.append((start + keep_gap, edge, 'silence+trailing-filler'))
        leading = [w for w in words if w.start < start]
        edge = start
        for w in reversed(leading):
            if w.end > start + .04 or edge - w.end > adjacency or normalize(w.text) not in fillers or start - w.start > 2:
                break
            edge = w.start
            options.append((edge, end - keep_gap, 'leading-filler+silence'))
    result = []
    for a, b, kind in options:
        # Inward rounding retains at least the requested quiet time.
        round_a = math.floor if kind == 'leading-filler+silence' else math.ceil
        round_b = math.ceil if kind == 'silence+trailing-filler' else math.floor
        a, b = round_a(a * fps) / fps, round_b(b * fps) / fps
        if a < 1 / fps or b - a < .1:
            continue
        if words and any(w.start < b - .001 and w.end > a + .001 and
                         (kind == 'silence' or normalize(w.text) not in fillers or a > w.start + .001 or b < w.end - .001)
                         for w in words):
            continue
        result.append(dict(start=a, end=b, kind=kind))
    return sorted(result, key=lambda x: x['end'] - x['start'], reverse=True)


def plan(pauses, fps, duration, judge, keep_gap=.5, words=None, fillers=DEFAULT_FILLERS):
    decisions, accepted = [], []
    for s, e in sorted(pauses, key=lambda p: p[1] - p[0], reverse=True):
        attempts = []
        chosen = None
        # Opening/closing silence has no speech on both sides; leave it untouched.
        options = candidates(s, e, fps, keep_gap, words, fillers) if s > 0 and e < duration - 1/fps else []
        for option in options:
            a, b = option['start'], option['end']
            if any(a < c['end'] and b > c['start'] for c in accepted):
                attempts.append(dict(**option, accepted=False, reason='overlapping cut'))
                continue
            check = judge(a - 1/fps, b)
            attempts.append(dict(**option, **check))
            if check['accepted']:
                chosen = option
                accepted.append(option)
                break
        decisions.append(dict(silence_start=s, silence_end=e, decision='CUT' if chosen else 'KEEP', attempts=attempts))
    return sorted(accepted, key=lambda c: c['start']), decisions
