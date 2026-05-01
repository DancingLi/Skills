# Skills

A collection of AI agent skills (OpenCode, Claude Code, Cursor, Trae, etc.) covering document generation, context management, and media processing.

## Skills

| Skill | Description |
|---|---|
| **cv-writing-expert** | AI-powered, ATS-optimized CV generation. Dual onboarding: build from scratch or refine an existing CV with STAR-method bullet crafting. |
| **Handoff_Context** | Generate a context handoff Markdown file (objectives, research, execution plan) for seamless AI session switching. |
| **html_css_to_pdf** | Convert HTML/CSS presentations to PDF while preserving all visual design — no layout loss. |
| **Presentation_Creator** | Auto-generate HTML+CSS presentation slides from Markdown content. Supports simple and interactive modes. |
| **video-transcription** | Batch pipeline: download video audio via yt-dlp, transcribe with local faster-whisper, correct ASR errors via LLM API. Manifest-driven with resume support. |

## Usage

Copy any skill folder to your AI tool's skills directory:

```bash
cp -r <skill-name> ~/.codex/skills/       # OpenCode
cp -r <skill-name> ~/.claude/skills/      # Claude Code
```

## License

MIT — see [LICENSE](LICENSE).
