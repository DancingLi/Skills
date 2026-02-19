# Presentation Creator

A skill for generating beautiful HTML+CSS presentations from Markdown content. Supports both simple and complex interaction modes.

## Features

- **Easy to Use**: Just write Markdown
- **Two Modes**: Simple and complex interaction modes
- **Modern Styling**: Purple-themed design with gradients
- **No Dependencies**: Pure HTML+CSS+JavaScript output

### Simple Mode
- Basic left/right navigation buttons
- Clean and minimal interface

### Complex Mode
- Keyboard navigation (arrow keys, PageUp/PageDown, space)
- Fullscreen toggle (press F)
- Progress bar
- Slide counter
- Navigation hints

## Prerequisites

```bash
pip install markdown
```

## Usage

```bash
python create_presentation.py --input <markdown_file> --mode [simple|complex] --output <output_dir>
```

## Parameters

| Parameter | Description | Required | Default |
|-----------|-------------|----------|---------|
| `--input` | Input Markdown file path | Yes | - |
| `--mode` | Interaction mode: `simple` or `complex` | No | `simple` |
| `--output` | Output directory path | No | `./presentation` |
| `--title` | Presentation title | No | `Presentation` |

## Markdown Format

Separate each slide with `---`:

```markdown
# First Slide Title

Content for the first slide...

---

# Second Slide Title

- List item 1
- List item 2

---

# Third Slide Title

More content...
```

## Supported Markdown Elements

- Headings (H1-H3)
- Paragraphs
- Ordered and unordered lists
- Code blocks with syntax highlighting
- Blockquotes
- Tables

## Examples

### Basic Usage
```bash
python create_presentation.py --input my_slides.md
```

### Complex Mode with Custom Title
```bash
python create_presentation.py \
    --input my_slides.md \
    --mode complex \
    --title "My Presentation" \
    --output ./my-presentation
```

## Output Files

| File | Description |
|------|-------------|
| `index.html` | Main HTML file with presentation structure |
| `styles.css` | Stylesheet with modern styling |

## Keyboard Shortcuts (Complex Mode)

| Key | Action |
|-----|--------|
| `←` or `PageUp` | Previous slide |
| `→`, `PageDown`, or `Space` | Next slide |
| `F` | Toggle fullscreen |

## Files

| File | Description |
|------|-------------|
| `SKILL.md` | Skill definition and instructions |
| `create_presentation.py` | Main script for generating presentations |
| `example.md` | Example Markdown input file |
| `requirements.txt` | Python dependencies |

## License

MIT License
