
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

