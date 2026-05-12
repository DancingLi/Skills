---
name: manuscript-guided-srt
description: Generate production-quality .srt subtitles by aligning local faster-whisper word timestamps to a clean speech manuscript. Use when audio was read from a script/manuscript, Whisper ASR has transcription errors or unnatural phrasing, timestamps must come from audio rather than an LLM, or the user needs reusable manuscript-guided subtitle generation for narration, voiceover, podcast, or video audio.
---

# Manuscript-Guided SRT

## Use This Workflow

Use the bundled script when the user has:

- an audio/video narration file
- a mostly correct manuscript or speech script
- a need for production-usable `.srt` subtitles
- a requirement that timestamps are generated from audio and not rewritten by an LLM

Do not use bulk LLM correction on timestamped SRT. If the user wants LLM polishing, only apply it after alignment to text-only cue batches while preserving cue IDs and cue count.

## Script

Run:

```powershell
python "<skill>/scripts/manuscript_guided_srt.py" `
  --audio "path\to\audio.mp3" `
  --manuscript "path\to\script.md" `
  --model "path\to\faster-whisper-model" `
  --language zh
```

The script writes defaults beside the audio unless `--output-dir`, `--srt-out`, `--words-json`, or `--report-out` is provided:

- `<audio_stem>_corrected.srt`
- `alignment/<audio_stem>_words.json`
- `alignment/<audio_stem>_alignment_report.md`

Prefer `WHISPER_MODEL_PATH` when available; otherwise pass `--model`. Keep VAD off unless there is a clear reason to enable it.

## Useful Options

- `--output-dir DIR`: put all generated outputs under a chosen directory.
- `--force-transcribe`: regenerate word timestamps instead of reusing existing JSON.
- `--term "Name"` or `--terms-file terms.txt`: include fragile names/phrases in the report.
- `--max-cue-chars`, `--max-line-chars`, `--min-duration`, `--max-duration`, `--max-chars-per-sec`: tune readability thresholds.
- `--device cuda --compute float16`: good GPU default.
- `--device cpu --compute int8`: CPU fallback.

## Validation Expectations

After generation, inspect the report first. A good run normally has:

- monotonic, non-overlapping SRT cues
- no large untimed manuscript spans
- a reasonable matched/interpolated ratio
- fragile terms present in the SRT when present in the manuscript

Spot-check report warnings in a subtitle editor before final delivery.
