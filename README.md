# Defaulter Letter Generator

Desktop app (customtkinter) that tracks student attendance and generates
attendance-shortage letters as PDFs for every student below a threshold.

## What changed from the original version

- **Lecture-weighted attendance.** Attendance is entered as attended lectures
  and total lectures for each subject. Overall theory attendance is calculated
  as total theory lectures attended divided by total theory lectures, so a
  subject with fewer lectures cannot outweigh the others. Practical subjects
  remain visible but are not included in the overall theory percentage.
- **Manual attendance entry with live percentages.** The Attendance tab was
  previously a Roll No/Name list with no way to enter numbers by hand. It's
  now a full pivoted table (one column per subject, colored red when a
  student is below the threshold). Click **"Add / Edit Attendance"** (or
  double-click a row) to open a per-subject entry form, pre-filled with the
  student's current values.
- **Faster, safer database layer.** One shared connection with WAL mode and
  indices instead of opening/closing a connection per query; a bulk-save
  helper so editing a student's whole attendance row is one transaction, not
  six.
- **PDF generation no longer requires MS Word.** `docx_to_pdf` tries, in
  order: `docx2pdf` (Word on Windows/Mac) → LibreOffice headless (`soffice`,
  works on Windows/Mac/Linux) → a reportlab fallback that always produces
  *something*. Install LibreOffice on the machine you package the exe for if
  you want the most faithful PDF output without needing Word.
- **Error handling & logging.** Import/generation errors show one message
  box instead of a crash; details go to `app.log` next to the exe.
- **Template filling is more robust** — it no longer assumes exactly 6
  attendance columns or that every placeholder sits in a single text run.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

`template.docx` in this folder is your actual St. John College attendance-
shortage letter, with the blank/dotted fields swapped for placeholders:
`{{date}}`, `{{parent_name}}`, `{{class}}`, `{{div}}`, `{{roll_no}}`,
`{{student_name}}`, `{{intimation_no}}`, `{{from_date}}`, `{{to_date}}`, and
`{{faculty_name}}` (filled into the Class Advisor signature line). Everything
else — logo, letterhead, subject-abbreviation legend, HoD/Principal
signature blocks — is untouched.

`pdf_utils.py` fills the attendance table by *scanning* for the row that
contains the subject codes and the "Roll No"/"Student Name" headers, then
writes into the row right below it — it doesn't hardcode a row/column
index, so reordering or adding subjects in the Subjects tab still lines up
correctly as long as the codes (T1, T2, ... P1, P2, ...) match what's in
the template.

Note: the address line right under the parent's name (second `……` block in
the original template) is left blank — the app doesn't currently collect a
parent address, so add it by hand in Word/PDF, or extend the Students tab
with an address field if you want it automated too.

Run it:

```bash
python app.py
```

## Day-to-day workflow

1. **Students tab** — import your class list from Excel (`Roll No, Student
   Name, Class, Div, Parent Name, Parent Contact`, use *Export Template* to
   get the exact column order), or add students one at a time.
2. **Subjects tab** — the six default subjects are seeded on first run; add,
   rename, or remove subjects here. Subject codes are what the Excel
   importer and the manual-entry form key off of.
3. **Attendance tab** — either:
   - **Upload Attendance Excel**: use *Export Template*. Each subject has
     two columns such as `T1 Present` and `T1 Lectures`; enter whole lecture
     counts in those columns; or
   - **Add / Edit Attendance**: pick a student and enter attended lectures
     and total lectures for each subject. The table shows each subject's
     percentage and the weighted overall theory percentage. Rows below the
     threshold turn red immediately.
4. **Generate Letters tab** — set the threshold, faculty name, date,
   intimation number, and from/to dates, then **Generate All PDFs**. One PDF
   per student below the threshold is written to the folder you choose, and
   a record of every generated letter is kept in **History**.

## Building a standalone .exe

```bash
pip install pyinstaller
pyinstaller build.spec
```

The output is `dist/DefaulterLetterGenerator/DefaulterLetterGenerator.exe`
(Windows) with `template.docx` bundled alongside it — copy the whole
`dist/DefaulterLetterGenerator` folder to distribute it, since `letters.db`
and `app.log` are created next to the exe on first run.

Build on the same OS you're targeting (build on Windows for a Windows exe).
For the most reliable PDF output on the target machine, install LibreOffice
there too — `docx2pdf` needs an actual MS Word install, and without either,
the app still runs but falls back to the plain-text reportlab renderer.

## Files

| File | Purpose |
|---|---|
| `app.py` | GUI — all five tabs |
| `database.py` | SQLite schema and queries |
| `pdf_utils.py` | Fills `template.docx` and converts it to PDF |
| `template.docx` | Your letter template (not included — see Setup) |
| `build.spec` | PyInstaller build configuration |
| `requirements.txt` | Python dependencies |