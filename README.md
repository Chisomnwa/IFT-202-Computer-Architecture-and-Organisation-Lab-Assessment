# IFT 212: Computer Architecture and Organization Lab Assessment

This repository contains the assessment brief, an editable report template, and Python checks for the Miva Open University IFT 212 lab assessment. The five assessments cover sequential instruction execution, pipeline scheduling, pipeline speedup, read-after-write (RAW) hazards, and hazard detection.

## What the checks cover

The verification script independently calculates and checks:

- Sequential cycle count, final register values, memory value, and CPI.
- Ideal five-stage pipeline schedules and total cycle counts.
- Speedup values for the five programs in the assessment.
- RAW dependencies and stall counts using a cycle-by-cycle pipeline simulation.
- Hazard detection for valid pipeline entries and the given pipeline snapshot.

The checks reproduce the calculations under the assumptions below. They are intended to catch inconsistent values or schedules; they are not a formal proof of processor correctness.

## Pipeline assumptions

- The pipeline has five stages: IF, ID, EX, MEM, and WB.
- Assessment 2 uses the question's ideal schedule with no hazards or stalls.
- Assessments 4 and 5 assume no forwarding. Register operands are read in ID and written in WB, with WB writes visible to ID reads in the same cycle.
- Hazard detection reports RAW matches; the stall logic separately determines whether a match still requires waiting.

## Repository layout

| Path | Purpose |
| --- | --- |
| `assessment/` | Original assessment brief |
| `report/solutions.tex` | Editable LaTeX report template; student identification fields are placeholders |
| `src/hazard_detection.py` | RAW hazard detection implementation |
| `scripts/verify_results.py` | Independent arithmetic, pipeline, dependency, and stall checks |
| `output/` | Local report build files; ignored by Git |
| `private/` | Local personalized report source; ignored by Git |

## Requirements

- Python 3.10 or newer.
- A LaTeX installation with `pdflatex` and the standard packages used by the report (`geometry`, `lmodern`, `longtable`, `tabularx`, `listings`, `fancyhdr`, `hyperref`, `amsmath`, and `needspace`).

## Run the verification checks

From the repository root, run:

```sh
python3 scripts/verify_results.py
```

The script prints each check as it runs and finishes with `All verification checks passed.` when all checks succeed.

## Compile the report template

The template leaves student identification fields as placeholders. Complete those fields in a local copy before using it for an individual submission. From the repository root, compile the report with:

```sh
mkdir -p output
pdflatex -interaction=nonstopmode -halt-on-error \
  -jobname=IFT-212-Lab-Assessment-Solutions \
  -output-directory=output report/solutions.tex
pdflatex -interaction=nonstopmode -halt-on-error \
  -jobname=IFT-212-Lab-Assessment-Solutions \
  -output-directory=output report/solutions.tex
```

Run `pdflatex` twice so the contents page and document links settle. The local build files are written to `output/`, which is excluded from version control. Keep personal student information in local files only; do not add it to the public template or other tracked files.
