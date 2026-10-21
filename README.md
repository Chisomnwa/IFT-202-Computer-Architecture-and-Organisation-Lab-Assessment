# IFT-212 Computer Architecture and Organization Lab Assessment

Solutions and verification materials for the Miva Open University IFT 212 lab assessment.

## Project contents

- `assessment/` - original assessment PDF
- `src/` - hazard detection implementation
- `scripts/` - independent calculation and pipeline verification
- `report/` - editable LaTeX report source
- `output/` - generated submission PDF (ignored by Git)

Run the checks with:

```sh
python3 scripts/verify_results.py
```

Compile the report from the repository root with:

```sh
pdflatex -interaction=nonstopmode -halt-on-error -jobname=IFT-212-Lab-Assessment-Solutions -output-directory=output report/solutions.tex
pdflatex -interaction=nonstopmode -halt-on-error -jobname=IFT-212-Lab-Assessment-Solutions -output-directory=output report/solutions.tex
```

The report currently uses placeholders for private student details. The final PDF and student-detail files are excluded from Git.
