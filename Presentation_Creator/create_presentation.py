#!/usr/bin/env python3
import argparse
import os
import markdown
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create HTML+CSS presentation from Markdown"
    )
    parser.add_argument("--input", required=True, help="Input Markdown file path")
    parser.add_argument(
        "--mode", default="simple", choices=["simple", "complex"], help="Interaction mode"
    )
    parser.add_argument(
        "--output", default="./presentation", help="Output directory path"
    )
    parser.add_argument(
        "--title", default="Presentation", help="Presentation title"
    )
    return parser.parse_args()


def read_markdown(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def parse_slides(markdown_content):
    slides = []
    raw_slides = markdown_content.strip().split("---")
    for raw_slide in raw_slides:
        if raw_slide.strip():
            html = markdown.markdown(raw_slide.strip(), extensions=["extra"])
            slides.append(html)
    return slides


def create_html_template(mode, title, slides):
    slide_html = ""
    for i, slide in enumerate(slides):
        active_class = "active" if i == 0 else ""
        slide_html += f'<div class="slide {active_class}" data-slide="{i}">{slide}</div>\n'

    if mode == "simple":
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="presentation">
        <div class="slides-container">
            {slide_html}
        </div>
        <button class="nav-btn prev-btn">&lt;</button>
        <button class="nav-btn next-btn">&gt;</button>
    </div>
    <script>
        const slides = document.querySelectorAll('.slide');
        let currentSlide = 0;

        function showSlide(index) {{
            slides.forEach((slide, i) => {{
                slide.classList.remove('active');
                if (i === index) {{
                    slide.classList.add('active');
                }}
            }});
        }}

        document.querySelector('.prev-btn').addEventListener('click', () => {{
            if (currentSlide > 0) {{
                currentSlide--;
                showSlide(currentSlide);
            }}
        }});

        document.querySelector('.next-btn').addEventListener('click', () => {{
            if (currentSlide < slides.length - 1) {{
                currentSlide++;
                showSlide(currentSlide);
            }}
        }});
    </script>
</body>
</html>"""
    else:
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="presentation">
        <div class="progress-bar">
            <div class="progress-fill" id="progressFill"></div>
        </div>
        <div class="slides-container">
            {slide_html}
        </div>
        <button class="nav-btn prev-btn">&lt;</button>
        <button class="nav-btn next-btn">&gt;</button>
        <div class="slide-counter"><span id="currentSlide">1</span> / <span id="totalSlides">{len(slides)}</span></div>
        <button class="fullscreen-btn" id="fullscreenBtn">⛶</button>
        <div class="controls-hint">← → 翻页 | F 全屏</div>
    </div>
    <script>
        const slides = document.querySelectorAll('.slide');
        let currentSlide = 0;
        const totalSlides = slides.length;

        function updateProgress() {{
            const progress = ((currentSlide + 1) / totalSlides) * 100;
            document.getElementById('progressFill').style.width = progress + '%';
            document.getElementById('currentSlide').textContent = currentSlide + 1;
        }}

        function showSlide(index) {{
            slides.forEach((slide, i) => {{
                slide.classList.remove('active');
                if (i === index) {{
                    slide.classList.add('active');
                }}
            }});
            updateProgress();
        }}

        function goToPrev() {{
            if (currentSlide > 0) {{
                currentSlide--;
                showSlide(currentSlide);
            }}
        }}

        function goToNext() {{
            if (currentSlide < totalSlides - 1) {{
                currentSlide++;
                showSlide(currentSlide);
            }}
        }}

        function toggleFullscreen() {{
            if (!document.fullscreenElement) {{
                document.documentElement.requestFullscreen();
            }} else {{
                document.exitFullscreen();
            }}
        }}

        document.querySelector('.prev-btn').addEventListener('click', goToPrev);
        document.querySelector('.next-btn').addEventListener('click', goToNext);
        document.getElementById('fullscreenBtn').addEventListener('click', toggleFullscreen);

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'ArrowLeft' || e.key === 'PageUp') {{
                goToPrev();
            }} else if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') {{
                e.preventDefault();
                goToNext();
            }} else if (e.key === 'f' || e.key === 'F') {{
                toggleFullscreen();
            }}
        }});

        updateProgress();
    </script>
</body>
</html>"""


def create_css_template(mode):
    if mode == "simple":
        return """* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    background: #1a1a2e;
    color: #eee;
    overflow: hidden;
    height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
}

.presentation {
    position: relative;
    width: 100%;
    height: 100%;
    max-width: 1200px;
    max-height: 900px;
}

.slides-container {
    width: 100%;
    height: 100%;
    position: relative;
}

.slide {
    position: absolute;
    width: 100%;
    height: 100%;
    padding: 80px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    opacity: 0;
    transition: opacity 0.4s ease;
}

.slide.active {
    opacity: 1;
    z-index: 1;
}

.slide h1 {
    font-size: 3.5rem;
    margin-bottom: 1.5rem;
    color: #a855f7;
}

.slide h2 {
    font-size: 2.5rem;
    margin-bottom: 1.2rem;
    color: #8b5cf6;
}

.slide h3 {
    font-size: 1.8rem;
    margin-bottom: 1rem;
    color: #c4b5fd;
}

.slide p {
    font-size: 1.5rem;
    line-height: 1.8;
    margin-bottom: 1rem;
}

.slide ul, .slide ol {
    font-size: 1.5rem;
    line-height: 2;
    margin-left: 2rem;
    margin-bottom: 1rem;
}

.slide li {
    margin-bottom: 0.5rem;
}

.slide code {
    background: rgba(255,255,255,0.1);
    padding: 0.2em 0.5em;
    border-radius: 4px;
    font-family: monospace;
}

.slide pre {
    background: rgba(0,0,0,0.4);
    padding: 1.5rem;
    border-radius: 8px;
    overflow-x: auto;
    margin-bottom: 1rem;
}

.slide pre code {
    background: transparent;
    padding: 0;
}

.slide blockquote {
    border-left: 4px solid #a855f7;
    padding-left: 1.5rem;
    margin: 1.5rem 0;
    font-style: italic;
    opacity: 0.9;
}

.nav-btn {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    background: rgba(168, 85, 247, 0.8);
    color: white;
    border: none;
    width: 60px;
    height: 60px;
    font-size: 2rem;
    cursor: pointer;
    border-radius: 50%;
    z-index: 10;
    transition: all 0.3s ease;
}

.nav-btn:hover {
    background: rgba(168, 85, 247, 1);
    transform: translateY(-50%) scale(1.1);
}

.prev-btn {
    left: 20px;
}

.next-btn {
    right: 20px;
}
"""
    else:
        return """* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    background: #0f0f23;
    color: #f0f0f0;
    overflow: hidden;
    height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
}

.presentation {
    position: relative;
    width: 100%;
    height: 100%;
    max-width: 1400px;
    max-height: 900px;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    box-shadow: 0 25px 80px rgba(0, 0, 0, 0.5);
    border-radius: 12px;
    overflow: hidden;
}

.progress-bar {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 6px;
    background: rgba(255, 255, 255, 0.1);
    z-index: 100;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #a855f7, #ec4899);
    width: 0%;
    transition: width 0.4s ease;
}

.slides-container {
    width: 100%;
    height: 100%;
    position: relative;
}

.slide {
    position: absolute;
    width: 100%;
    height: 100%;
    padding: 100px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    opacity: 0;
    transform: scale(0.95);
    transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide.active {
    opacity: 1;
    transform: scale(1);
    z-index: 1;
}

.slide h1 {
    font-size: 4rem;
    margin-bottom: 1.5rem;
    background: linear-gradient(90deg, #a855f7, #ec4899);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.slide h2 {
    font-size: 2.8rem;
    margin-bottom: 1.2rem;
    color: #c4b5fd;
}

.slide h3 {
    font-size: 2rem;
    margin-bottom: 1rem;
    color: #ddd6fe;
}

.slide p {
    font-size: 1.6rem;
    line-height: 1.9;
    margin-bottom: 1rem;
}

.slide ul, .slide ol {
    font-size: 1.6rem;
    line-height: 2.2;
    margin-left: 2.5rem;
    margin-bottom: 1rem;
}

.slide li {
    margin-bottom: 0.6rem;
}

.slide code {
    background: rgba(168, 85, 247, 0.2);
    padding: 0.25em 0.6em;
    border-radius: 6px;
    font-family: "Consolas", "Monaco", monospace;
    color: #f0abfc;
}

.slide pre {
    background: rgba(0, 0, 0, 0.5);
    padding: 1.8rem;
    border-radius: 12px;
    overflow-x: auto;
    margin-bottom: 1rem;
    border: 1px solid rgba(168, 85, 247, 0.3);
}

.slide pre code {
    background: transparent;
    padding: 0;
    color: #e9d5ff;
}

.slide blockquote {
    border-left: 5px solid #a855f7;
    padding-left: 2rem;
    margin: 2rem 0;
    font-style: italic;
    opacity: 0.9;
    background: rgba(168, 85, 247, 0.1);
    padding: 1.5rem 2rem;
    border-radius: 0 8px 8px 0;
}

.slide table {
    width: 100%;
    border-collapse: collapse;
    margin: 1.5rem 0;
}

.slide th, .slide td {
    border: 1px solid rgba(255, 255, 255, 0.2);
    padding: 1rem;
    text-align: left;
}

.slide th {
    background: rgba(168, 85, 247, 0.3);
}

.nav-btn {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    background: linear-gradient(135deg, rgba(168, 85, 247, 0.9), rgba(236, 72, 153, 0.9));
    color: white;
    border: none;
    width: 70px;
    height: 70px;
    font-size: 2.2rem;
    cursor: pointer;
    border-radius: 50%;
    z-index: 10;
    transition: all 0.3s ease;
    box-shadow: 0 8px 25px rgba(168, 85, 247, 0.4);
}

.nav-btn:hover {
    transform: translateY(-50%) scale(1.15);
    box-shadow: 0 12px 35px rgba(168, 85, 247, 0.6);
}

.prev-btn {
    left: 30px;
}

.next-btn {
    right: 30px;
}

.slide-counter {
    position: absolute;
    bottom: 30px;
    right: 40px;
    font-size: 1.2rem;
    color: rgba(255, 255, 255, 0.7);
    z-index: 10;
}

.fullscreen-btn {
    position: absolute;
    top: 20px;
    right: 30px;
    background: rgba(255, 255, 255, 0.1);
    color: white;
    border: none;
    width: 45px;
    height: 45px;
    font-size: 1.5rem;
    cursor: pointer;
    border-radius: 8px;
    z-index: 100;
    transition: all 0.3s ease;
}

.fullscreen-btn:hover {
    background: rgba(168, 85, 247, 0.8);
}

.controls-hint {
    position: absolute;
    bottom: 30px;
    left: 40px;
    font-size: 0.95rem;
    color: rgba(255, 255, 255, 0.5);
    z-index: 10;
}
"""


def main():
    args = parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    markdown_content = read_markdown(args.input)
    slides = parse_slides(markdown_content)

    html_content = create_html_template(args.mode, args.title, slides)
    css_content = create_css_template(args.mode)

    html_path = output_dir / "index.html"
    css_path = output_dir / "styles.css"

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    with open(css_path, "w", encoding="utf-8") as f:
        f.write(css_content)

    print(f"✅ Presentation created successfully!")
    print(f"📁 Output directory: {output_dir.absolute()}")
    print(f"📄 Files: index.html, styles.css")
    print(f"🎯 Mode: {args.mode}")
    print(f"📊 Slides: {len(slides)}")


if __name__ == "__main__":
    main()
