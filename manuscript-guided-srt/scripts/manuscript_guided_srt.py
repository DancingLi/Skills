from __future__ import annotations

import argparse
import difflib
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CleanChar:
    ch: str
    orig: int


@dataclass
class TimedChar:
    ch: str
    start: float
    end: float
    source_text: str


def is_kept_char(ch: str) -> bool:
    return (
        "\u4e00" <= ch <= "\u9fff"
        or "\u3040" <= ch <= "\u30ff"
        or "\uac00" <= ch <= "\ud7af"
        or ch.isalnum()
        or ch in "-._/:&"
    )


def normalize_char(ch: str) -> str:
    return ch.lower() if ch.isascii() else ch


def clean_entries(text: str) -> list[CleanChar]:
    return [CleanChar(normalize_char(ch), i) for i, ch in enumerate(text) if is_kept_char(ch)]


def clean_text(text: str) -> str:
    return "".join(e.ch for e in clean_entries(text))


def fmt_srt_time(t: float) -> str:
    t = max(0.0, t)
    ms_total = int(round(t * 1000))
    h, rem = divmod(ms_total, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def compact_subtitle_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text.replace("\r", "\n")).strip()
    text = re.sub(r"\s+([，。！？、：；）》】])", r"\1", text)
    text = re.sub(r"([（《【])\s+", r"\1", text)
    return text


def move_to_safe_text_boundary(text: str, pos: int) -> int:
    if pos <= 1 or pos >= len(text):
        return pos
    if not (text[pos - 1].isascii() and text[pos].isascii()):
        return pos

    right = pos
    while right < len(text) and text[right - 1].isascii() and text[right].isascii():
        right += 1
    left = pos
    while left > 1 and text[left - 1].isascii() and text[left].isascii():
        left -= 1

    if right < len(text) and abs(right - pos) <= abs(pos - left) + 4:
        return right
    if left > 1:
        return left
    return pos


def split_for_two_lines(text: str, max_line_chars: int) -> str:
    if len(text) <= max_line_chars:
        return text

    candidates = []
    for i, ch in enumerate(text):
        if ch in "，、；： -":
            pos = i + 1
            if pos < len(text) and text[pos - 1].isascii() and text[pos].isascii():
                continue
            candidates.append(pos)
    midpoint = len(text) / 2
    split_at = min(candidates, key=lambda p: abs(p - midpoint)) if candidates else move_to_safe_text_boundary(text, int(midpoint))

    left = text[:split_at].strip()
    right = text[split_at:].strip()
    return f"{left}\n{right}" if left and right else text


def resolve_outputs(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    audio = Path(args.audio)
    base_dir = Path(args.output_dir) if args.output_dir else audio.parent
    stem = audio.stem
    srt_out = Path(args.srt_out) if args.srt_out else base_dir / f"{stem}_corrected.srt"
    alignment_dir = base_dir / "alignment"
    words_json = Path(args.words_json) if args.words_json else alignment_dir / f"{stem}_words.json"
    report_out = Path(args.report_out) if args.report_out else alignment_dir / f"{stem}_alignment_report.md"
    return srt_out, words_json, report_out


def load_terms(args: argparse.Namespace) -> list[str]:
    terms = list(args.term or [])
    if args.terms_file:
        path = Path(args.terms_file)
        terms.extend(
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        )
    seen = set()
    result = []
    for term in terms:
        if term not in seen:
            seen.add(term)
            result.append(term)
    return result


def validate_inputs(args: argparse.Namespace, words_json: Path) -> str | None:
    audio = Path(args.audio)
    manuscript = Path(args.manuscript)
    if not audio.exists():
        raise SystemExit(f"Audio file not found: {audio}")
    if not manuscript.exists():
        raise SystemExit(f"Manuscript file not found: {manuscript}")
    if not words_json.exists() or args.force_transcribe:
        model_path = args.model or os.environ.get("WHISPER_MODEL_PATH")
        if not model_path:
            raise SystemExit("No word timestamp JSON exists and no model was provided. Pass --model or set WHISPER_MODEL_PATH.")
        if not Path(model_path).exists():
            raise SystemExit(f"Model path not found: {model_path}")
        return model_path
    return None


def save_word_timestamps(
    audio: Path,
    words_json: Path,
    model_path: str,
    language: str,
    device: str,
    compute_type: str,
    beam_size: int,
    vad_filter: bool,
) -> None:
    from faster_whisper import WhisperModel

    model = WhisperModel(model_path, device=device, compute_type=compute_type)
    segments, info = model.transcribe(
        str(audio),
        language=language,
        vad_filter=vad_filter,
        beam_size=beam_size,
        word_timestamps=True,
    )

    out_segments = []
    for seg in segments:
        words = []
        for word in seg.words or []:
            words.append(
                {
                    "word": word.word,
                    "start": word.start,
                    "end": word.end,
                    "probability": getattr(word, "probability", None),
                }
            )
        out_segments.append({"id": seg.id, "start": seg.start, "end": seg.end, "text": seg.text, "words": words})

    payload = {
        "audio": str(audio),
        "model": model_path,
        "language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
        "segments": out_segments,
    }
    words_json.parent.mkdir(parents=True, exist_ok=True)
    words_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def timed_asr_chars(words_payload: dict) -> list[TimedChar]:
    chars: list[TimedChar] = []
    for seg in words_payload.get("segments", []):
        words = seg.get("words") or []
        if not words:
            text = seg.get("text", "")
            cleaned = clean_text(text)
            if not cleaned:
                continue
            start = float(seg["start"])
            end = float(seg["end"])
            dur = max(0.01, end - start)
            for i, ch in enumerate(cleaned):
                chars.append(TimedChar(ch, start + dur * i / len(cleaned), start + dur * (i + 1) / len(cleaned), text))
            continue

        for word in words:
            raw = word.get("word") or ""
            cleaned = clean_text(raw)
            if not cleaned:
                continue
            start = float(word["start"])
            end = float(word["end"])
            dur = max(0.01, end - start)
            for i, ch in enumerate(cleaned):
                chars.append(TimedChar(ch, start + dur * i / len(cleaned), start + dur * (i + 1) / len(cleaned), raw.strip()))
    return chars


def map_manuscript_times(asr_chars: list[TimedChar], manuscript_entries: list[CleanChar], max_interpolate_chars: int, max_interpolate_seconds: float) -> tuple[list[float | None], list[float | None], dict]:
    asr_clean = "".join(c.ch for c in asr_chars)
    manu_clean = "".join(c.ch for c in manuscript_entries)
    matcher = difflib.SequenceMatcher(None, asr_clean, manu_clean, autojunk=False)

    starts: list[float | None] = [None] * len(manuscript_entries)
    ends: list[float | None] = [None] * len(manuscript_entries)
    matched = 0

    for asr_pos, manu_pos, length in matcher.get_matching_blocks():
        if length == 0:
            continue
        matched += length
        for offset in range(length):
            asr_char = asr_chars[asr_pos + offset]
            idx = manu_pos + offset
            starts[idx] = asr_char.start
            ends[idx] = asr_char.end

    filled = 0
    i = 0
    while i < len(starts):
        if starts[i] is not None:
            i += 1
            continue
        gap_start = i
        while i < len(starts) and starts[i] is None:
            i += 1
        gap_end = i
        prev_idx = gap_start - 1
        next_idx = gap_end
        if prev_idx >= 0 and next_idx < len(starts) and starts[prev_idx] is not None and starts[next_idx] is not None:
            prev_t = ends[prev_idx] or starts[prev_idx] or 0.0
            next_t = starts[next_idx] or prev_t
            gap_len = gap_end - gap_start
            time_gap = next_t - prev_t
            if gap_len <= max_interpolate_chars and 0 <= time_gap <= max_interpolate_seconds:
                step = max(0.04, time_gap / (gap_len + 1))
                for j in range(gap_len):
                    cs = prev_t + step * (j + 1)
                    starts[gap_start + j] = cs
                    ends[gap_start + j] = min(cs + step * 0.85, next_t)
                    filled += 1

    stats = {
        "asr_chars": len(asr_chars),
        "manuscript_chars": len(manuscript_entries),
        "matched_chars": matched,
        "filled_chars": filled,
        "timed_chars": sum(1 for t in starts if t is not None),
    }
    stats["asr_to_manuscript_ratio"] = (len(asr_chars) / len(manuscript_entries)) if manuscript_entries else 0.0
    stats["interpolation_ratio"] = (filled / len(manuscript_entries)) if manuscript_entries else 0.0
    stats["direct_match_ratio"] = (matched / len(manuscript_entries)) if manuscript_entries else 0.0
    return starts, ends, stats


def sentence_boundaries(manuscript: str, entries: list[CleanChar], starts: list[float | None], max_cue_chars: int) -> list[tuple[int, int]]:
    boundaries: list[tuple[int, int]] = []
    cue_start = 0
    last_break = 0
    strong_punct = set("。！？!?")
    soft_punct = set("，、；：,;:")

    for clean_idx, entry in enumerate(entries):
        orig = entry.orig
        next_orig = entries[clean_idx + 1].orig if clean_idx + 1 < len(entries) else len(manuscript)
        between = manuscript[orig + 1 : next_orig]
        cue_len = clean_idx - cue_start + 1
        safe_boundary = True
        if clean_idx + 1 < len(entries):
            safe_boundary = not (entries[clean_idx].ch.isascii() and entries[clean_idx + 1].ch.isascii())

        should_break = False
        if any(ch in strong_punct for ch in between):
            should_break = True
        elif cue_len >= max(8, int(max_cue_chars * 0.53)) and any(ch in soft_punct or ch == "\n" for ch in between):
            should_break = True
        elif cue_len >= max_cue_chars and safe_boundary:
            should_break = True

        if should_break:
            boundaries.append((cue_start, clean_idx + 1))
            cue_start = clean_idx + 1
            last_break = clean_idx + 1

    if last_break < len(entries):
        boundaries.append((last_break, len(entries)))

    merged: list[tuple[int, int]] = []
    for start, end in boundaries:
        has_time = any(starts[i] is not None for i in range(start, end))
        if not has_time and merged:
            ps, _ = merged[-1]
            merged[-1] = (ps, end)
        else:
            merged.append((start, end))
    return merged


def cue_text_from_clean_span(manuscript: str, entries: list[CleanChar], start: int, end: int) -> str:
    orig_start = entries[start].orig
    orig_end = entries[end - 1].orig + 1
    while orig_start > 0 and manuscript[orig_start - 1] in "（《【“\"'":
        orig_start -= 1
    while orig_end < len(manuscript) and manuscript[orig_end] in "，。！？!?；：、）》】”\"'":
        orig_end += 1
    return compact_subtitle_text(manuscript[orig_start:orig_end])


def build_cues(manuscript: str, entries: list[CleanChar], starts: list[float | None], ends: list[float | None], max_cue_chars: int, min_duration: float) -> list[dict]:
    cues = []
    for start_idx, end_idx in sentence_boundaries(manuscript, entries, starts, max_cue_chars):
        timed = [i for i in range(start_idx, end_idx) if starts[i] is not None]
        if not timed:
            continue
        start = starts[timed[0]]
        end = ends[timed[-1]] or starts[timed[-1]]
        if start is None or end is None:
            continue
        if end - start < min_duration:
            end = start + min_duration
        text = cue_text_from_clean_span(manuscript, entries, start_idx, end_idx)
        if text:
            cues.append({"start": start, "end": end, "text": text, "clean_start": start_idx, "clean_end": end_idx})

    for i in range(1, len(cues)):
        prev = cues[i - 1]
        cur = cues[i]
        if cur["start"] < prev["end"] + 0.02:
            midpoint = (prev["end"] + cur["start"]) / 2
            prev["end"] = max(prev["start"] + min_duration, midpoint - 0.01)
            cur["start"] = max(prev["end"] + 0.02, cur["start"])
            if cur["end"] <= cur["start"]:
                cur["end"] = cur["start"] + min_duration
    return cues


def write_srt(cues: list[dict], path: Path, max_line_chars: int) -> None:
    parts = []
    for idx, cue in enumerate(cues, 1):
        parts.append(str(idx))
        parts.append(f"{fmt_srt_time(cue['start'])} --> {fmt_srt_time(cue['end'])}")
        parts.append(split_for_two_lines(cue["text"], max_line_chars))
        parts.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts), encoding="utf-8")


def ranges_without_time(starts: list[float | None]) -> list[tuple[int, int]]:
    ranges = []
    i = 0
    while i < len(starts):
        if starts[i] is not None:
            i += 1
            continue
        start = i
        while i < len(starts) and starts[i] is None:
            i += 1
        ranges.append((start, i))
    return ranges


def manuscript_excerpt(manuscript: str, entries: list[CleanChar], start: int, end: int, limit: int = 80) -> str:
    if start >= len(entries):
        return ""
    orig_start = entries[start].orig
    orig_end = entries[min(end, len(entries)) - 1].orig + 1
    text = compact_subtitle_text(manuscript[orig_start:orig_end])
    return text[:limit] + ("..." if len(text) > limit else "")


def write_report(path: Path, cues: list[dict], manuscript: str, entries: list[CleanChar], starts: list[float | None], stats: dict, terms: list[str], args: argparse.Namespace) -> None:
    warnings = []
    if stats["asr_to_manuscript_ratio"] < args.min_length_ratio or stats["asr_to_manuscript_ratio"] > args.max_length_ratio:
        warnings.append(f"- ASR/manuscript length ratio is suspicious: {stats['asr_to_manuscript_ratio']:.3f}")
    if stats["interpolation_ratio"] > args.max_interpolation_ratio:
        warnings.append(f"- High interpolation ratio: {stats['interpolation_ratio']:.1%}")
    if stats["direct_match_ratio"] < args.min_direct_match_ratio:
        warnings.append(f"- Low direct match ratio: {stats['direct_match_ratio']:.1%}")

    for idx, cue in enumerate(cues, 1):
        dur = cue["end"] - cue["start"]
        clean_len = cue["clean_end"] - cue["clean_start"]
        cps = clean_len / dur if dur > 0 else math.inf
        if dur < args.min_duration:
            warnings.append(f"- Cue {idx}: very short duration {dur:.2f}s")
        if dur > args.max_duration:
            warnings.append(f"- Cue {idx}: long duration {dur:.2f}s")
        if cps > args.max_chars_per_sec:
            warnings.append(f"- Cue {idx}: high reading speed {cps:.1f} chars/s")
        if idx > 1 and cue["start"] < cues[idx - 2]["end"]:
            warnings.append(f"- Cue {idx}: overlaps previous cue")

    untimed = ranges_without_time(starts)
    untimed_lines = [f"- clean chars {s}-{e}: {manuscript_excerpt(manuscript, entries, s, e)}" for s, e in untimed[:50]]

    lines = [
        "# Manuscript Alignment Report",
        "",
        "## Summary",
        f"- ASR clean chars: {stats['asr_chars']}",
        f"- Manuscript clean chars: {stats['manuscript_chars']}",
        f"- ASR/manuscript ratio: {stats['asr_to_manuscript_ratio']:.3f}",
        f"- Direct matched chars: {stats['matched_chars']} ({stats['direct_match_ratio']:.1%})",
        f"- Interpolated chars: {stats['filled_chars']} ({stats['interpolation_ratio']:.1%})",
        f"- Timed manuscript chars: {stats['timed_chars']}",
        f"- SRT cues: {len(cues)}",
        "",
        "## Warnings",
        *(warnings[:120] or ["- None"]),
        "",
        "## Untimed Manuscript Spans",
        *(untimed_lines or ["- None"]),
    ]
    if terms:
        lines.extend(["", "## Fragile Term Check"])
        for term in terms:
            present = term in manuscript
            in_srt = any(term in cue["text"] for cue in cues)
            lines.append(f"- `{term}`: manuscript={'yes' if present else 'no'}, srt={'yes' if in_srt else 'no'}")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_srt_time(ts: str) -> int:
    h = int(ts[0:2])
    m = int(ts[3:5])
    s = int(ts[6:8])
    ms = int(ts[9:12])
    return ((h * 60 + m) * 60 + s) * 1000 + ms


def validate_srt(path: Path) -> tuple[int, list[str]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return 0, ["empty SRT"]
    blocks = [block for block in re.split(r"\n\s*\n", text) if block.strip()]
    bad = []
    prev_end = -1
    time_re = re.compile(r"^(\d\d:\d\d:\d\d,\d\d\d) --> (\d\d:\d\d:\d\d,\d\d\d)$")
    for expected, block in enumerate(blocks, 1):
        lines = block.splitlines()
        if len(lines) < 3 or lines[0] != str(expected):
            bad.append(f"cue {expected}: bad block shape")
            continue
        match = time_re.match(lines[1])
        if not match:
            bad.append(f"cue {expected}: bad time line")
            continue
        start = parse_srt_time(match.group(1))
        end = parse_srt_time(match.group(2))
        if start < prev_end:
            bad.append(f"cue {expected}: overlaps previous cue")
        if end <= start:
            bad.append(f"cue {expected}: non-positive duration")
        prev_end = end
    return len(blocks), bad


def run(args: argparse.Namespace) -> None:
    audio = Path(args.audio)
    manuscript_path = Path(args.manuscript)
    srt_out, words_json, report_out = resolve_outputs(args)
    terms = load_terms(args)
    model_path = validate_inputs(args, words_json)

    if not words_json.exists() or args.force_transcribe:
        assert model_path is not None
        print(f"[transcribe] {audio}")
        save_word_timestamps(audio, words_json, model_path, args.language, args.device, args.compute, args.beam_size, args.vad)
        print(f"[out] words: {words_json}")
    else:
        print(f"[reuse] words: {words_json}")

    manuscript = manuscript_path.read_text(encoding="utf-8")
    entries = clean_entries(manuscript)
    words_payload = json.loads(words_json.read_text(encoding="utf-8"))
    asr_chars = timed_asr_chars(words_payload)
    starts, ends, stats = map_manuscript_times(asr_chars, entries, args.max_interpolate_chars, args.max_interpolate_seconds)
    cues = build_cues(manuscript, entries, starts, ends, args.max_cue_chars, args.min_duration)

    write_srt(cues, srt_out, args.max_line_chars)
    write_report(report_out, cues, manuscript, entries, starts, stats, terms, args)

    cue_count, srt_errors = validate_srt(srt_out)
    if srt_errors:
        print(f"[warn] SRT validation found {len(srt_errors)} issue(s):")
        for item in srt_errors[:20]:
            print(f"  {item}")
    else:
        print(f"[check] SRT parse OK: {cue_count} cues")

    print(f"[out] SRT: {srt_out}")
    print(f"[out] report: {report_out}")
    print(f"[done] {len(cues)} cues, {stats['timed_chars']}/{stats['manuscript_chars']} timed manuscript chars")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate manuscript-guided SRT with faster-whisper word timestamps.")
    parser.add_argument("--audio", required=True)
    parser.add_argument("--manuscript", required=True)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--srt-out", default="")
    parser.add_argument("--words-json", default="")
    parser.add_argument("--report-out", default="")
    parser.add_argument("--model", default="", help="Local faster-whisper model path. Falls back to WHISPER_MODEL_PATH.")
    parser.add_argument("--language", default="zh")
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"])
    parser.add_argument("--compute", default="float16")
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--vad", action="store_true", help="Enable VAD. Default is off.")
    parser.add_argument("--force-transcribe", action="store_true")
    parser.add_argument("--term", action="append", default=[])
    parser.add_argument("--terms-file", default="")
    parser.add_argument("--max-cue-chars", type=int, default=34)
    parser.add_argument("--max-line-chars", type=int, default=22)
    parser.add_argument("--min-duration", type=float, default=0.45)
    parser.add_argument("--max-duration", type=float, default=7.0)
    parser.add_argument("--max-chars-per-sec", type=float, default=9.5)
    parser.add_argument("--max-interpolate-chars", type=int, default=80)
    parser.add_argument("--max-interpolate-seconds", type=float, default=35.0)
    parser.add_argument("--min-length-ratio", type=float, default=0.75)
    parser.add_argument("--max-length-ratio", type=float, default=1.25)
    parser.add_argument("--max-interpolation-ratio", type=float, default=0.25)
    parser.add_argument("--min-direct-match-ratio", type=float, default=0.65)
    return parser


if __name__ == "__main__":
    run(build_parser().parse_args())
