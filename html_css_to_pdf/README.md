# HTML/CSS to PDF Converter

A skill for converting HTML/CSS presentations to PDF format while preserving all visual design elements.

## Features

- Preserves all colors and gradients
- Maintains exact font styles and sizes
- Keeps original layout and spacing
- One slide per PDF page
- Automatically hides UI navigation elements
- Supports code blocks, tables, and blockquotes

## When to Use

Invoke this skill when:

- You have an HTML/CSS presentation to convert to PDF
- You need to preserve all design elements (gradients, colors, fonts, layout)
- The presentation uses slide-based navigation (one slide per view)

## Prerequisites

Check if the required dependencies are installed:

```bash
pip show playwright pypdf2
```

If not installed, run:

```bash
pip install playwright pypdf2
playwright install chromium
```

## Usage

### Step 1: Create the Conversion Script

Create a Python script (e.g., `generate_pdf.py`) in the same directory as your `index.html`:

```python
from playwright.sync_api import sync_playwright
import os
import tempfile

def generate_presentation_pdf():
    temp_dir = tempfile.mkdtemp()
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1400, 'height': 900})
        
        html_path = os.path.abspath('index.html')
        page.goto(f'file://{html_path}')
        page.wait_for_load_state('networkidle')
        
        total_slides = page.evaluate("document.querySelectorAll('.slide').length")
        pdf_files = []
        
        for slide_idx in range(total_slides):
            page.evaluate("""
                (idx) => {
                    const slides = document.querySelectorAll('.slide');
                    slides.forEach((slide, i) => {
                        slide.classList.remove('active');
                        if (i === idx) {
                            slide.classList.add('active');
                        }
                    });
                    
                    const elementsToHide = [
                        '.nav-btn', '.next-btn', '.prev-btn', '.slide-counter',
                        '.fullscreen-btn', '.controls-hint', '.progress-bar'
                    ];
                    elementsToHide.forEach(sel => {
                        const el = document.querySelector(sel);
                        if (el) el.style.display = 'none';
                    });
                }
            """, slide_idx)
            
            page.wait_for_timeout(200)
            
            pdf_path = os.path.join(temp_dir, f'slide_{slide_idx:02d}.pdf')
            page.pdf(
                path=pdf_path,
                format='A4',
                landscape=True,
                print_background=True,
                margin={'top': '0', 'bottom': '0', 'left': '0', 'right': '0'}
            )
            pdf_files.append(pdf_path)
        
        browser.close()
        
        from PyPDF2 import PdfMerger
        merger = PdfMerger()
        for pdf in pdf_files:
            merger.append(pdf)
        
        output_path = 'presentation.pdf'
        merger.write(output_path)
        merger.close()
        
        for pdf in pdf_files:
            os.remove(pdf)
        os.rmdir(temp_dir)
        
        print(f'PDF generated successfully: {output_path}')

if __name__ == '__main__':
    generate_presentation_pdf()
```

### Step 2: Customize for Your Presentation

| Setting | Description |
|---------|-------------|
| **Slide Selector** | Change `.slide` to match your slide elements' class/selector |
| **UI Elements to Hide** | Adjust the `elementsToHide` list to match your presentation's controls |
| **Viewport Size** | Modify `viewport={'width': 1400, 'height': 900}` to match your slide dimensions |
| **Output PDF Name** | Change `'presentation.pdf'` to your desired filename |

### Step 3: Run the Script

```bash
python generate_pdf.py
```

## Output

- `presentation.pdf` - Merged PDF with all slides

## Troubleshooting

### Model Download Issues
If Playwright browsers fail to download:
```bash
playwright install chromium --with-deps
```

### Font Rendering Issues
Ensure your system has the required fonts installed.

### Slide Dimensions
If slides are cut off, adjust the `viewport` dimensions or PDF `format`/`margin` settings.

## Files

| File | Description |
|------|-------------|
| `SKILL.md` | Skill definition and instructions |
| `generate_pdf_template.py` | Template script for PDF generation |

## License

MIT License
