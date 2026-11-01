"""Generate editable LaTeX, compile PDF, and package an Overleaf-only ZIP."""
from pathlib import Path
import subprocess
import zipfile
ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
subprocess.run(["pandoc", "manuscript.md", "--from=markdown+tex_math_single_backslash", "--standalone", "--shift-heading-level-by=-1", "--variable=papersize:a4", "--citeproc", "--bibliography=references.bib", "--include-in-header=header.tex", "--variable=documentclass:ctexart", "--variable=classoption:fontset=fandol", "--variable=geometry:margin=23mm", "--variable=fontsize:11pt", "--output=main.tex"], cwd=PAPER, check=True)
subprocess.run(["tectonic", "--keep-logs", "main.tex"], cwd=PAPER, check=True)
with zipfile.ZipFile(PAPER / "overleaf.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for name in ("main.tex", "references.bib", "header.tex"):
        archive.write(PAPER / name, name)
print("Compiled paper/main.pdf and packaged paper/overleaf.zip")
