import argparse
import json
import math
from pathlib import Path
import sys
from . import __version__
from . import media, transcript
from .core import plan


def positive(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError('Must be a finite positive number.')
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description='Sniplet: conservative silence cuts for stationary single-person shots. MVP; review every result.')
    parser.add_argument('input', type=Path)
    parser.add_argument('-o', '--output', type=Path, required=True)
    parser.add_argument('--report', type=Path, help='Default: OUTPUT.plan.json')
    parser.add_argument('--analyze-only', action='store_true')
    parser.add_argument('--transcript', type=Path, help='Opt in to adjacent filler trimming using millisecond word-level SRT/VTT/JSON.')
    parser.add_argument('--fillers', default='um,uh,erm,er', help='Comma-separated filler words; requires --transcript.')
    parser.add_argument('--min-silence', type=positive, default=.85)
    parser.add_argument('--noise-db', type=float, default=-34)
    parser.add_argument('--keep-gap', type=positive, default=.5, help='Seconds of real silence retained (minimum 0.5).')
    parser.add_argument('--motion-scale', type=positive, default=1, help='Multiply visual limits; larger values allow more movement.')
    args = parser.parse_args(argv)
    try:
        source, output = args.input.resolve(), args.output.resolve()
        report = (args.report or output.with_suffix('.plan.json')).resolve()
        if not source.is_file():
            raise ValueError('Input file not found.')
        protected = {source}
        if args.transcript:
            protected.add(args.transcript.resolve())
        if output in protected or report in protected or output == report or output.exists() or report.exists():
            raise ValueError('Choose unused output and report paths, separate from inputs.')
        if args.keep_gap < .5:
            raise ValueError('--keep-gap must be at least 0.5 seconds.')
        if not math.isfinite(args.noise_db) or not -100 <= args.noise_db < 0:
            raise ValueError('--noise-db must be between -100 and 0 dBFS (exclusive of 0).')
        if not args.transcript and args.fillers != 'um,uh,erm,er':
            raise ValueError('--fillers requires --transcript.')
        info = media.probe(source)
        words = transcript.load(args.transcript, info['duration']) if args.transcript else None
        fillers = frozenset(transcript.normalize(w) for w in args.fillers.split(',') if w.strip())
        if not fillers:
            raise ValueError('Supply at least one filler word.')
        source_hash = media.fingerprint(source)
        pauses = media.silences(source, info['duration'], args.noise_db, args.min_silence)
        print(f'Found {len(pauses)} pauses. Checking longest first...', flush=True)
        from .vision import Judge
        judge = Judge(source, args.motion_scale)
        try:
            cuts, decisions = plan(pauses, info['fps'], info['duration'], judge, args.keep_gap, words, fillers)
        finally:
            judge.close()
        result = dict(version=__version__, source=str(source), source_sha256=source_hash, media=info,
                      settings=dict(min_silence=args.min_silence, noise_db=args.noise_db, keep_gap=args.keep_gap,
                                    motion_scale=args.motion_scale, filler_mode=bool(words), fillers=sorted(fillers) if words else []),
                      cuts=cuts, decisions=decisions, removed_seconds=sum(c['end']-c['start'] for c in cuts))
        if media.fingerprint(source) != source_hash:
            raise RuntimeError('Source changed during analysis; refusing to render.')
        with report.open('x', encoding='utf-8') as f:
            json.dump(result, f, indent=2, allow_nan=False)
        if not args.analyze_only:
            verification = media.render(source, output, cuts, info)
            if media.fingerprint(source) != source_hash:
                raise RuntimeError('Source changed during rendering; review output before use.')
            print(f'Output duration verified: {verification["output_duration"]:.3f}s')
        print(f'{len(cuts)} cuts; {result["removed_seconds"]:.2f}s removed. Report: {report}')
        print('MVP: watch and listen to the result before publishing.')
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as exc:
        print(f'Sniplet: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
