---
name: video-transcription
description: >-
  Batch pipeline for downloading audio from online videos, transcribing with local faster-whisper,
  and optionally correcting ASR errors via LLM API (DeepSeek/OpenAI). Use when the user asks to
  transcribe videos, download YouTube/Bilibili audio for ASR, batch-process video transcripts,
  correct whisper ASR output, or build a manifest-driven video-to-text workflow.
---

# Video Transcription

## Overview

Manifest-driven 5-phase pipeline: init -> enrich -> download -> transcribe -> correct.

Each phase reads `manifest.json`, processes only `pending` entries, writes back. Resumable from any breakpoint. All outputs preserved -- nothing overwritten without explicit intent.

Unified script: `scripts/pipeline.py` with subcommand phases.

## Prerequisites

Verify these before starting:

- `yt-dlp` on PATH (run `yt-dlp --version`)
- `faster-whisper` installed (`pip install faster-whisper`)  
- Whisper model pre-downloaded to a known directory (large-v3 or turbo recommended)
- For correction: `pip install requests` + API key in env var (`DEEPSEEK_API_KEY` or `OPENAI_API_KEY`)

## Workflow

### Step 0 -- Confirm project directory

Ask the user for a project directory. Create one if new:
```
mkdir <project-dir>
```

Run `pipeline.py` with `-d <project-dir>`. All outputs live in subdirectories `audio/`, `transcripts_raw/`, `transcripts_corrected/`. File naming: `{index:03d}_{source_id}.{ext}`.

### Step 1 -- Init manifest

```bash
python scripts/pipeline.py init -d <dir> --url-file urls.txt
# or
python scripts/pipeline.py init -d <dir> --url URL1 --url URL2
```

Creates `manifest.json` with entries having `index`, `source_id`, `url`, status fields all `pending`. Always clean tracking params from URLs.

### Step 2 -- Enrich metadata

```bash
python scripts/pipeline.py enrich -d <dir>
```

Runs `yt-dlp --dump-json` on all URLs, fills in `title`, `publish_date`, `part`. Flags multi-part videos.

### Step 3 -- Download audio

```bash
python scripts/pipeline.py download -d <dir>
```

Downloads mp3 audio via `yt-dlp -x --audio-format mp3`. Uses `--download-archive` (auto) to prevent re-downloads on resume. 1s delay between requests.

### Step 4 -- Transcribe

```bash
python scripts/pipeline.py transcribe -d <dir> --model /path/to/whisper-model --language zh
```

Options: `--device cuda|cpu`, `--compute float16|int8`, `--vad` (off by default), `--language` (use `""` for auto-detect).

Output: timestamped `[XX.Xs - YY.Ys] text` format.

### Step 5 -- Correct (optional)

```bash
python scripts/pipeline.py correct -d <dir> --provider deepseek
```

**Before running**: Confirm authorization to send transcripts to external API. Run security scan -- the script uses regex patterns (not substring) to detect credentials. Content about "tokens" in LLM context will NOT be flagged (only `sk-...` patterns, `api_key=...`, etc.).

Options: `--provider openai`, `--correction-model gpt-4o`, `--spot-check 3`.

After correction, auto spot-checks N random transcripts and reports word-change ratio. Warns if >15%.

### Quick commands

```bash
python scripts/pipeline.py status -d <dir>     # per-entry status table
python scripts/pipeline.py summary -d <dir>    # aggregate stats
python scripts/pipeline.py all -d <dir> --model /path --language zh  # full run
```

## Critical Defaults

These are baked in -- do not change without understanding the consequences:

| Default | Rationale |
|---|---|
| VAD off (`--vad` enables) | VAD can silently produce empty transcripts for valid speech |
| Regex security scan, not substring | "token" in tech videos != credential. Only `sk-...`, `api_key=...` etc. |
| `--download-archive` on by default | Idempotent -- safe to re-run without re-downloading |
| Model path required, no auto-download | Avoids HF mirror/DNS issues. Model must be pre-downloaded |
| Correction prompt is fixed | Crafted and tested -- restricts to ASR errors only, no summarization |
| Manifest as single source of truth | All phases read/write same JSON. Rename manual changes |
| 1s delay between downloads/API calls | Rate limiting for polite operation |

## Troubleshooting

**HF model download fails (DNS/timeout):**
Set env var `HF_ENDPOINT=https://hf-mirror.com` or use a pre-downloaded model with `--model /local/path`.

**VAD produces empty transcripts for valid audio:**
VAD is off by default. If you enabled `--vad` and got empty output, re-run without it.

**"Transcribe failed" for valid-looking audio files:**
The audio likely contains only music (no speech). Check RMS energy manually or mark as `no-speech-audio` in manifest.

**Correction flags "token" as sensitive:**
Already fixed -- the security scanner uses regex, not substring matching. Should not happen.

**Resuming after partial run:**
Just re-run the same phase. It processes only `pending` entries. Downloaded files with `--download-archive` are skipped.

## Manifest Schema

```json
{
  "index": 1,
  "source_id": "BV1Hp9UBgESH",
  "url": "https://www.bilibili.com/video/BV1Hp9UBgESH",
  "title": "Video title",
  "publish_date": "20260429",
  "part": "",
  "download_status": "done|failed|pending",
  "transcribe_status": "done|failed|pending",
  "correction_status": "done|failed|pending|skipped",
  "notes": ""
}
```

Status values flow one direction: `pending` -> `done` / `failed` / `skipped`. Reset a status to `pending` to re-process individual entries.
