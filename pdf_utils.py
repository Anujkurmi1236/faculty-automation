"""
Fills the defaulter-letter .docx template and converts it to PDF.

Changes vs. the original version:
  * `fill_template()` now only writes the subjects that exist for this
    student (previously it silently wrote a value into an attendance
    column even if that subject was blank/missing for the student, and
    assumed exactly 6 subject columns starting at cell index 3).
  * Conversion order is: docx2pdf (Word, Windows/Mac) -> LibreOffice
    headless (`soffice`, works on Windows/Mac/Linux and is what most
    packaged installs will actually have available) -> reportlab table
    fallback (so the app never produces zero output even with nothing
    else installed).
  * Logging instead of bare `print()`, and every step returns/raises
    something the caller can act on.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
from typing import Any, Optional

from docx import Document
from docx.document import Document as DocumentType

log = logging.getLogger("defaulter_app.pdf_utils")


def replace_in_paragraph(paragraph, replacements: dict) -> None:
    """Replace {{placeholder}} tokens, tolerant of Word splitting a token
    across multiple runs (which happens often once autocorrect / spell-check
    touches the template)."""
    full_text = paragraph.text
    if not any(key in full_text for key in replacements):
        return

    # Simple case: token lives entirely inside one run.
    for key, val in replacements.items():
        for run in paragraph.runs:
            if key in run.text:
                run.text = run.text.replace(key, val)

    # Fallback for tokens split across runs: rebuild the paragraph text only
    # if a placeholder is still present after the per-run pass above.
    remaining = paragraph.text
    if any(key in remaining for key in replacements) and paragraph.runs:
        new_text = remaining
        for key, val in replacements.items():
            new_text = new_text.replace(key, val)
        if new_text != remaining:
            paragraph.runs[0].text = new_text
            for run in paragraph.runs[1:]:
                run.text = ""


def fill_template(
    template_path: str,
    data: dict,
    subjects: list[dict],
    attendance: dict,
    save_docx_path: str,
) -> str:
    """
    data       : dict with date, class, div, roll_no, student_name,
                 intimation_no, from_date, to_date, faculty_name
    subjects   : list of dicts  [{'code':'T1','name':'Design of Experiments (DOE)'}, ...]
    attendance : dict  {'T1': 68.0, 'T2': 72.0, ...}
    """
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Letter template not found: {template_path}")

    doc = Document(template_path)

    replacements = {
        "{{date}}": data.get("date", ""),
        "{{class}}": data.get("class", ""),
        "{{div}}": data.get("div", ""),
        "{{roll_no}}": data.get("roll_no", ""),
        "{{student_name}}": data.get("student_name", ""),
        "{{parent_name}}": data.get("parent_name", ""),
        "{{intimation_no}}": data.get("intimation_no", ""),
        "{{from_date}}": data.get("from_date", ""),
        "{{to_date}}": data.get("to_date", ""),
        "{{faculty_name}}": data.get("faculty_name", ""),
    }

    for para in doc.paragraphs:
        replace_in_paragraph(para, replacements)
    for tbl in doc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    replace_in_paragraph(para, replacements)

    _fill_attendance_table(doc, data, subjects, attendance)

    doc.save(save_docx_path)
    return save_docx_path


def _fill_attendance_table(doc: DocumentType, data: dict, subjects: list[dict], attendance: dict) -> None:
    """Locate the attendance table's subject-code row and the data row right
    below it, then fill Roll No / Student Name / each subject's percentage.

    This doesn't assume a fixed row/column index - it looks for the row
    whose cells contain "Roll No", "Student Name" and the subject codes
    (subject columns are frequently horizontally merged in these letter
    templates, e.g. one cell spanning both the "P1" and its duplicate grid
    position - python-docx exposes merged cells as the *same* cell object
    at each grid index it spans, so writing to one index is enough).
    """
    codes = {s["code"] for s in subjects}

    for table in doc.tables:
        header_row_idx = None
        col_map: dict[str, int] = {}
        roll_col = name_col = None

        for ridx, row in enumerate(table.rows):
            # Dedup merged cells: python-docx repeats the same underlying
            # cell object at every grid index it spans, so key by identity
            # and keep only the first index for each distinct cell.
            local_map: dict[int, tuple[int, str]] = {}
            for cidx, cell in enumerate(row.cells):
                key = id(cell._tc)
                if key not in local_map:
                    local_map[key] = (cidx, cell.text.strip())

            texts_lower = {v[1].lower() for v in local_map.values()}
            code_hits = sum(1 for v in local_map.values() if v[1] in codes)
            has_roll = any("roll no" in t for t in texts_lower)
            has_name = any("student name" in t for t in texts_lower)

            if code_hits >= max(1, len(codes) // 2) and has_roll and has_name:
                header_row_idx = ridx
                for _, (cidx, text) in local_map.items():
                    if text in codes:
                        col_map[text] = cidx
                    elif "roll no" in text.lower():
                        roll_col = cidx
                    elif "student name" in text.lower():
                        name_col = cidx
                break

        if header_row_idx is None or header_row_idx + 1 >= len(table.rows):
            continue  # not the attendance table (or no data row below it)

        data_row = table.rows[header_row_idx + 1]
        if roll_col is not None:
            data_row.cells[roll_col].text = data.get("roll_no", "")
        if name_col is not None:
            data_row.cells[name_col].text = data.get("student_name", "")
        for code, cidx in col_map.items():
            val = attendance.get(code)
            if val is None:
                data_row.cells[cidx].text = "-"
            elif isinstance(val, (int, float)):
                data_row.cells[cidx].text = f"{val:g}"
            else:
                data_row.cells[cidx].text = str(val)
        return  # attendance table found and filled; stop looking


def _convert_with_docx2pdf(docx_path: str, pdf_path: str) -> Optional[str]:
    try:
        from docx2pdf import convert
        convert(docx_path, pdf_path)
        return pdf_path if os.path.exists(pdf_path) else None
    except Exception as e:
        log.info("docx2pdf unavailable/failed (%s) - trying next method", e)
        return None


def _convert_with_libreoffice(docx_path: str, pdf_path: str) -> Optional[str]:
    """Convert via LibreOffice/OpenOffice headless mode. Cross-platform and
    the most reliable option when the app is packaged as a standalone exe
    on a machine without MS Word installed."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None
    out_dir = os.path.dirname(pdf_path) or "."
    try:
        subprocess.run(
            [soffice, "--headless", "--norestore", "--convert-to", "pdf",
             "--outdir", out_dir, docx_path],
            check=True, timeout=60,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        produced = os.path.join(out_dir, os.path.splitext(os.path.basename(docx_path))[0] + ".pdf")
        if os.path.exists(produced):
            if produced != pdf_path:
                shutil.move(produced, pdf_path)
            return pdf_path
    except Exception as e:
        log.info("LibreOffice conversion failed (%s) - trying next method", e)
    return None


def _convert_with_reportlab(docx_path: str, pdf_path: str) -> Optional[str]:
    """Last-resort fallback: re-render paragraphs and tables with reportlab
    so the app still produces *a* PDF even with nothing else installed."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        doc = Document(docx_path)
        c = canvas.Canvas(pdf_path, pagesize=A4)
        width, height = A4
        y = height - 40

        def new_page_if_needed(min_y=40):
            nonlocal y
            if y < min_y:
                c.showPage()
                y = height - 40

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                y -= 8
                continue
            new_page_if_needed()
            c.setFont("Helvetica", 10)
            c.drawString(40, y, text[:110])
            y -= 14

        for table in doc.tables:
            y -= 10
            for row in table.rows:
                new_page_if_needed()
                cells = " | ".join(cell.text.strip() for cell in row.cells)
                c.setFont("Helvetica", 8)
                c.drawString(40, y, cells[:130])
                y -= 12

        c.save()
        return pdf_path
    except Exception as e:
        log.error("reportlab fallback failed: %s", e)
        return None


def docx_to_pdf(docx_path: str, pdf_path: str) -> Optional[str]:
    """Convert docx -> pdf, trying the most faithful method first and
    degrading gracefully if it isn't available on this machine."""
    for method in (_convert_with_docx2pdf, _convert_with_libreoffice, _convert_with_reportlab):
        result = method(docx_path, pdf_path)
        if result:
            return result
    log.error("All PDF conversion methods failed for %s", docx_path)
    return None