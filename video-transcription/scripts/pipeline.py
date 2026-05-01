"""
Video transcription pipeline with manifest-based state tracking.
Usage: python pipeline.py <phase> --project-dir <dir> [options]

Phases: init, enrich, download, transcribe, correct, summary, status, all
"""
import json
import subprocess
import sys
import os
import time
import re
from pathlib import Path


# ── Manifest helpers ──────────────────────────────────────────────


def load_manifest(project_dir):
    path = Path(project_dir) / "manifest.json"
    if not path.exists():
        print(f"ERROR: manifest.json not found in {project_dir}")
        print("  Run 'pipeline.py init' first or create one manually.")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_manifest(data, project_dir):
    path = Path(project_dir) / "manifest.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def index_str(idx):
    return f"{int(idx):03d}"


def audio_path(project_dir, entry):
    return Path(project_dir) / "audio" / f"{index_str(entry['index'])}_{entry['source_id']}.mp3"


def raw_path(project_dir, entry):
    return Path(project_dir) / "transcripts_raw" / f"{index_str(entry['index'])}_{entry['source_id']}.txt"


def corrected_path(project_dir, entry):
    return Path(project_dir) / "transcripts_corrected" / f"{index_str(entry['index'])}_{entry['source_id']}.txt"


def ensure_dirs(project_dir):
    for d in ["audio", "transcripts_raw", "transcripts_corrected"]:
        (Path(project_dir) / d).mkdir(parents=True, exist_ok=True)


# ── Phase: init ───────────────────────────────────────────────────


def phase_init(project_dir, urls=None, url_file=None):
    """Bootstrap manifest from URL list or file."""
    manifest_path = Path(project_dir) / "manifest.json"
    if manifest_path.exists():
        print("[init] manifest.json already exists. Use 'enrich' instead, or delete it first.")
        return

    lines = []
    if url_file:
        with open(url_file, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
    elif urls:
        lines = list(urls)

    if not lines:
        print("[init] No URLs provided. Use --urls or --url-file.")
        return

    data = []
    for i, url in enumerate(lines, 1):
        # Extract source_id from URL (bvid for bilibili, video_id for youtube, etc.)
        source_id = url.rstrip("/").split("/")[-1].split("?")[0]
        data.append({
            "index": i,
            "source_id": source_id,
            "url": url.split("?")[0],  # strip tracking params
            "title": "",
            "publish_date": "",
            "part": "",
            "download_status": "pending",
            "transcribe_status": "pending",
            "correction_status": "pending",
            "notes": "",
        })

    save_manifest(data, project_dir)
    print(f"[init] Created manifest.json with {len(data)} entries.")


# ── Phase: enrich ─────────────────────────────────────────────────


def phase_enrich(project_dir):
    """Fetch video metadata via yt-dlp --dump-json."""
    data = load_manifest(project_dir)
    urls = [e["url"] for e in data]
    print(f"[enrich] Fetching metadata for {len(urls)} videos...")

    tmp = Path(project_dir) / ".urls_tmp.txt"
    with open(tmp, "w", encoding="utf-8") as f:
        for url in urls:
            f.write(url + "\n")

    result = subprocess.run(
        ["yt-dlp", "--dump-json", "--no-download", "--ignore-errors", "-a", str(tmp)],
        capture_output=True, text=True
    )
    tmp.unlink(missing_ok=True)

    if result.returncode != 0:
        print(f"[enrich] yt-dlp stderr: {result.stderr[-500:]}")

    fetched = {}
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        try:
            info = json.loads(line)
            sid = info.get("id", "")
            if sid:
                fetched[sid] = info
        except json.JSONDecodeError:
            print(f"[enrich] Skipping malformed line: {line[:80]}...")

    for entry in data:
        sid = entry["source_id"]
        if sid in fetched:
            info = fetched[sid]
            entry["title"] = info.get("title", "") or info.get("fulltitle", "") or ""
            entry["publish_date"] = info.get("upload_date", "")
            n_entries = info.get("n_entries", 1) or 1
            entry["part"] = str(n_entries) if n_entries > 1 else ""
            entry["notes"] = "multi-part" if n_entries > 1 else ""
            print(f"  [{index_str(entry['index'])}] {sid}: {entry['title'][:60]} ({entry['publish_date']})")
        else:
            entry["notes"] = "metadata fetch failed"
            print(f"  [{index_str(entry['index'])}] {sid}: METADATA FETCH FAILED")

    save_manifest(data, project_dir)
    print(f"[enrich] Done. Updated {len(fetched)}/{len(urls)} entries.\n")


# ── Phase: download ───────────────────────────────────────────────


def phase_download(project_dir):
    """Download audio for all videos with pending download_status."""
    ensure_dirs(project_dir)
    data = load_manifest(project_dir)
    pending = [e for e in data if e["download_status"] == "pending"]
    if not pending:
        print("[download] No pending downloads.")
        return

    print(f"[download] Downloading audio for {len(pending)} videos...")
    archive = Path(project_dir) / "audio" / "downloaded.txt"

    for entry in pending:
        idx = entry["index"]
        sid = entry["source_id"]
        tmpl = str(Path(project_dir) / "audio" / f"{index_str(idx)}_{sid}.%(ext)s")

        cmd = [
            "yt-dlp", "-x", "--audio-format", "mp3",
            "-o", tmpl,
            "--download-archive", str(archive),
            "--no-playlist",
            entry["url"]
        ]

        print(f"  [{index_str(idx)}] Downloading {sid}...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            entry["download_status"] = "done"
            entry["notes"] = (entry.get("notes", "") + " downloaded").strip()
        else:
            entry["download_status"] = "failed"
            entry["notes"] = (entry.get("notes", "") + f" dl-failed:{result.stderr[-200:]}").strip()
            print(f"  [{index_str(idx)}] FAILED: {result.stderr[-200:]}")

        save_manifest(data, project_dir)
        time.sleep(1)

    done = sum(1 for e in data if e["download_status"] == "done")
    failed = sum(1 for e in data if e["download_status"] == "failed")
    print(f"[download] Done. {done} success, {failed} failed.\n")


# ── Phase: transcribe ─────────────────────────────────────────────


def phase_transcribe(project_dir, model_path, device="cuda", compute_type="float16",
                     language="zh", vad_filter=False, beam_size=5):
    """Transcribe audio using faster-whisper (local model at model_path)."""
    from faster_whisper import WhisperModel

    ensure_dirs(project_dir)
    data = load_manifest(project_dir)
    pending = [e for e in data if e["download_status"] == "done" and e["transcribe_status"] == "pending"]
    if not pending:
        print("[transcribe] No pending transcriptions.")
        return

    print(f"[transcribe] Transcribing {len(pending)} audio files ({language}, {device}/{compute_type})...")
    print(f"[transcribe] Loading model from {model_path}...")

    model = WhisperModel(model_path, device=device, compute_type=compute_type)

    for entry in pending:
        idx = entry["index"]
        sid = entry["source_id"]
        apath = audio_path(project_dir, entry)
        opath = raw_path(project_dir, entry)

        if not apath.exists():
            entry["transcribe_status"] = "failed"
            entry["notes"] = (entry.get("notes", "") + " audio-file-missing").strip()
            print(f"  [{index_str(idx)}] SKIP: audio file not found")
            save_manifest(data, project_dir)
            continue

        print(f"  [{index_str(idx)}] Transcribing {sid}...")
        try:
            segments, info = model.transcribe(
                str(apath),
                language=language,
                vad_filter=vad_filter,
                beam_size=beam_size,
            )

            lines = [f"# Duration: {info.duration:.1f}s | Language: {info.language} (prob={info.language_probability:.2f})", ""]
            for seg in segments:
                ts = f"[{seg.start:05.1f}s - {seg.end:05.1f}s]"
                lines.append(f"{ts} {seg.text.strip()}")

            with open(opath, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            entry["transcribe_status"] = "done"
            entry["notes"] = (entry.get("notes", "") + " transcribed").strip()
            print(f"    -> {opath.name} ({info.duration:.0f}s, {len(lines)-2} segments)")
        except Exception as exc:
            entry["transcribe_status"] = "failed"
            entry["notes"] = (entry.get("notes", "") + f" tr-failed:{str(exc)[:100]}").strip()
            print(f"  [{index_str(idx)}] FAILED: {exc}")

        save_manifest(data, project_dir)

    done = sum(1 for e in data if e["transcribe_status"] == "done")
    failed = sum(1 for e in data if e["transcribe_status"] == "failed")
    print(f"[transcribe] Done. {done} success, {failed} failed.\n")


# ── Phase: correct ────────────────────────────────────────────────

CORRECTION_PROMPT = (
    "你是一个ASR转写后处理工具。你的唯一任务是修正语音识别（ASR）产生的转写错误，"
    "包括：明显错字、专有名词错误、标点符号和断句。\n"
    "严格规则：\n"
    "1. 只修正ASR错误，不总结、不扩写、不改写语气、不改变含义。\n"
    "2. 保留原有的时间戳格式 [XX.Xs - YY.Ys]。\n"
    "3. 保留原有的段落结构和顺序。\n"
    "4. 对不确定的内容，保留原文不做修改。\n"
    "5. 输出完整的修正后文本，不要添加任何解释或标注。"
)

SENSITIVE_REGEX = [
    r'sk-[a-zA-Z0-9]{20,}',
    r'api[_-]?key\s*[:=]\s*[\S]{8,}',
    r'password\s*[:=]\s*\S{4,}',
    r'Bearer\s+[a-zA-Z0-9\-_\.]{20,}',
    r'secret\s*[:=]\s*\S{8,}',
    r'access[_-]?key\s*[:=]\s*\S{8,}',
]


def security_scan(text):
    """Scan text for credential patterns. Returns list of matches (empty = clean)."""
    found = []
    for pat in SENSITIVE_REGEX:
        matches = re.findall(pat, text, re.IGNORECASE)
        if matches:
            found.append(str(matches[0])[:60])
    return found


def phase_correct(project_dir, api_key=None, provider="deepseek", model_name="deepseek-chat",
                  spot_check=3, warn_threshold=0.15):
    """Correct ASR errors via LLM API."""
    import requests

    if not api_key:
        env_map = {"deepseek": "DEEPSEEK_API_KEY", "openai": "OPENAI_API_KEY"}
        api_key = os.environ.get(env_map.get(provider, env_map["deepseek"]), "")

    if not api_key:
        provider_env = env_map.get(provider, f"{provider.upper()}_API_KEY")
        print(f"[correct] SKIP: No API key. Set {provider_env} env var or pass --api-key.")
        return

    api_urls = {
        "deepseek": "https://api.deepseek.com/v1/chat/completions",
        "openai": "https://api.openai.com/v1/chat/completions",
    }
    api_url = api_urls.get(provider, api_urls["deepseek"])

    ensure_dirs(project_dir)
    data = load_manifest(project_dir)
    pending = [e for e in data if e["transcribe_status"] == "done" and e["correction_status"] == "pending"]
    if not pending:
        print("[correct] No pending corrections.")
        return

    print(f"[correct] Correcting {len(pending)} transcripts via {provider} ({model_name})...")

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    for entry in pending:
        idx = entry["index"]
        sid = entry["source_id"]
        rp = raw_path(project_dir, entry)
        cp = corrected_path(project_dir, entry)

        if not rp.exists():
            entry["correction_status"] = "failed"
            entry["notes"] = (entry.get("notes", "") + " raw-missing").strip()
            save_manifest(data, project_dir)
            continue

        with open(rp, "r", encoding="utf-8") as f:
            raw_text = f.read()

        sensitive = security_scan(raw_text)
        if sensitive:
            print(f"  [{index_str(idx)}] SKIP: credentials detected ({sensitive})")
            entry["correction_status"] = "skipped"
            entry["notes"] = (entry.get("notes", "") + " skipped:sensitive").strip()
            save_manifest(data, project_dir)
            continue

        print(f"  [{index_str(idx)}] Sending to {provider}...")
        try:
            resp = requests.post(api_url, headers=headers, json={
                "model": model_name,
                "messages": [
                    {"role": "system", "content": CORRECTION_PROMPT},
                    {"role": "user", "content": raw_text}
                ],
                "temperature": 0.1,
                "max_tokens": 65536,
            }, timeout=300)

            if resp.status_code == 200:
                corrected = resp.json()["choices"][0]["message"]["content"]
                with open(cp, "w", encoding="utf-8") as f:
                    f.write(corrected)
                entry["correction_status"] = "done"
                entry["notes"] = (entry.get("notes", "") + " corrected").strip()
                print(f"    -> {cp.name}")
            else:
                entry["correction_status"] = "failed"
                entry["notes"] = (entry.get("notes", "") + f" api-err-{resp.status_code}").strip()
                print(f"  [{index_str(idx)}] API ERROR {resp.status_code}: {resp.text[:200]}")
        except Exception as exc:
            entry["correction_status"] = "failed"
            entry["notes"] = (entry.get("notes", "") + f" cor-exc:{str(exc)[:100]}").strip()
            print(f"  [{index_str(idx)}] EXCEPTION: {exc}")

        save_manifest(data, project_dir)
        time.sleep(1)

    # Spot-check: compare N random raw vs corrected
    if spot_check > 0:
        corrected_entries = [e for e in data if e["correction_status"] == "done"]
        if len(corrected_entries) >= spot_check:
            import random
            samples = random.sample(corrected_entries, min(spot_check, len(corrected_entries)))
            print(f"\n[correct] Spot-checking {len(samples)} transcripts...")
            for e in samples:
                rp = raw_path(project_dir, e)
                cp = corrected_path(project_dir, e)
                raw = rp.read_text(encoding="utf-8") if rp.exists() else ""
                cor = cp.read_text(encoding="utf-8") if cp.exists() else ""
                if raw and cor:
                    raw_words = set(raw.split())
                    cor_words = set(cor.split())
                    if raw_words:
                        change_ratio = 1 - len(raw_words & cor_words) / len(raw_words)
                        flag = " ⚠ OVER-CORRECTED" if change_ratio > warn_threshold else ""
                        print(f"  [{index_str(e['index'])}] {e['source_id']}: word-change ratio {change_ratio:.1%}{flag}")

    done = sum(1 for e in data if e["correction_status"] == "done")
    failed = sum(1 for e in data if e["correction_status"] == "failed")
    print(f"[correct] Done. {done} success, {failed} failed.\n")


# ── Phase: summary / status ───────────────────────────────────────


def phase_summary(project_dir):
    """Print final summary of all work."""
    data = load_manifest(project_dir)
    downloaded = sum(1 for e in data if e["download_status"] == "done")
    transcribed = sum(1 for e in data if e["transcribe_status"] == "done")
    corrected = sum(1 for e in data if e["correction_status"] == "done")
    failed_dl = sum(1 for e in data if e["download_status"] == "failed")
    failed_tr = sum(1 for e in data if e["transcribe_status"] == "failed")
    failed_co = sum(1 for e in data if e["correction_status"] == "failed")

    print(f"{'='*60}")
    print(f"SUMMARY ── {Path(project_dir).name}")
    print(f"{'='*60}")
    print(f"  Total entries:     {len(data)}")
    print(f"  Downloaded:        {downloaded} (failed: {failed_dl})")
    print(f"  Transcribed:       {transcribed} (failed: {failed_tr})")
    print(f"  Corrected:         {corrected} (failed: {failed_co})")
    print(f"  Audio files:       {len(list((Path(project_dir)/'audio').glob('*.mp3')))}")
    print(f"  Raw transcripts:   {len(list((Path(project_dir)/'transcripts_raw').glob('*.txt')))}")
    print(f"  Corrected:         {len(list((Path(project_dir)/'transcripts_corrected').glob('*.txt')))}")
    print(f"{'='*60}")


def phase_status(project_dir):
    """Print per-entry status table."""
    data = load_manifest(project_dir)
    STAT = {"done": "✓", "failed": "✗", "pending": "·", "skipped": "−"}
    print(f"{'#':>3s} {'Source ID':<16s} {'Dl':>3s} {'Tr':>3s} {'Co':>3s} {'Title'}")
    print("-" * 80)
    for e in data:
        dl = STAT.get(e["download_status"], "?")
        tr = STAT.get(e["transcribe_status"], "?")
        co = STAT.get(e["correction_status"], "?")
        print(f"{e['index']:3d} {e['source_id']:<16s}  {dl}   {tr}   {co}  {e.get('title','')[:45]}")


# ── Main CLI ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Video Transcription Pipeline")
    parser.add_argument("phase", nargs="?", default="all",
                        choices=["init", "enrich", "download", "transcribe", "correct", "summary", "status", "all"])
    parser.add_argument("--project-dir", "-d", default=".", help="Project directory (where manifest.json lives)")
    parser.add_argument("--url", action="append", dest="urls", help="URL for init (repeatable)")
    parser.add_argument("--url-file", help="File with one URL per line for init")
    parser.add_argument("--model", default="", help="faster-whisper model path (required for transcribe)")
    parser.add_argument("--device", default="cuda", help="Device: cuda, cpu")
    parser.add_argument("--compute", default="float16", help="Compute type: float16, int8, float32")
    parser.add_argument("--language", "-l", default="zh", help="Language code for ASR (auto if empty)")
    parser.add_argument("--vad", action="store_true", help="Enable VAD filter (off by default)")
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--api-key", help="LLM API key for correction")
    parser.add_argument("--provider", default="deepseek", help="LLM provider: deepseek, openai")
    parser.add_argument("--correction-model", default="deepseek-chat", help="LLM model name")
    parser.add_argument("--spot-check", type=int, default=3, help="Number of transcripts to spot-check after correction")
    args = parser.parse_args()

    phase = args.phase
    proj = args.project_dir

    if phase in ("init", "all"):
        phase_init(proj, urls=args.urls, url_file=args.url_file)

    if phase in ("enrich", "all"):
        phase_enrich(proj)

    if phase in ("download", "all"):
        phase_download(proj)

    if phase in ("transcribe", "all"):
        model_path = args.model
        if not model_path:
            model_path = os.environ.get("WHISPER_MODEL_PATH", "")
        if not model_path:
            print("ERROR: --model is required for transcribe phase (path to faster-whisper model directory)")
            sys.exit(1)
        language = args.language if args.language else None
        phase_transcribe(proj, model_path, args.device, args.compute, language, args.vad, args.beam_size)

    if phase in ("correct", "all"):
        phase_correct(proj, args.api_key, args.provider, args.correction_model,
                      spot_check=args.spot_check)

    if phase in ("summary", "all"):
        phase_summary(proj)

    if phase == "status":
        phase_status(proj)
