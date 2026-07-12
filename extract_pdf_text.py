from pathlib import Path
import sys
from PyPDF2 import PdfReader
pdf_path = Path('Problem Statement Hackathon 4 Series.pdf')
if not pdf_path.exists():
    print('MISSING', pdf_path)
    sys.exit(1)
reader = PdfReader(str(pdf_path))
for i, page in enumerate(reader.pages):
    text = page.extract_text() or ''
    print(f'--- PAGE {i+1} ---')
    print(text)
    print()