from pathlib import Path
import re, zipfile
import fitz
root=Path(__file__).resolve().parents[1]
p=root/'paper'
keys=set(re.findall(r'@\w+\s*\{\s*([^,]+),',(p/'references.bib').read_text()))
cites=set(re.findall(r'@([A-Za-z0-9_:-]+)',(p/'manuscript.md').read_text()))
assert cites <= keys, f'Unknown citations: {cites-keys}'
assert (p/'main.pdf').read_bytes().startswith(b'%PDF-')
with fitz.open(p/'main.pdf') as pdf:
 text=''.join(page.get_text() for page in pdf)
assert 'RoboIDF' in text and '参考文献' in text
assert len(text)>5000, 'Unexpectedly short PDF'
log=(p/'main.log').read_text(errors='replace')
assert 'Missing character:' not in log, 'Missing glyphs'
assert 'undefined references' not in log, 'Undefined references'
with zipfile.ZipFile(p/'overleaf.zip') as z:
 assert set(z.namelist())=={'main.tex','header.tex','references.bib'}
print(f'PASS {len(cites)} citations, PDF text, glyphs, and Overleaf archive')
