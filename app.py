"""
app.py
------
Defaulter Letter Generator - desktop GUI (customtkinter).

Changes vs. the original version:
  * Attendance tab now shows a real pivoted table (Roll No | Name | one
    column per subject) with each student's percentage, colour-coded red
    when below the threshold - not just an empty Roll/Name list.
  * "Add / Edit Attendance" - double-click a student row (or pick one and
    click the button) to open a form with one entry box per subject,
    pre-filled with their current percentage, saved in a single
    transaction. This covers manual entry, which the Excel importer alone
    didn't.
  * Threshold changes now live-refresh the attendance table's colour
    coding and the defaulter list, instead of only affecting "Generate".
  * Centralised error handling (`_safe`) so a bad Excel file or a missing
    template shows one clear message box instead of a raw traceback.
  * Logging to a rotating file next to the exe, useful for diagnosing
    issues on a faculty member's machine after the app is packaged.
"""
from __future__ import annotations

import functools
import logging
import logging.handlers
import os
import sys
import datetime
import tempfile
from typing import Any, Optional
from typing import cast

import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
from openpyxl import load_workbook, Workbook
from openpyxl.worksheet.worksheet import Worksheet

import database
import pdf_utils


def resource_path(rel: str) -> str:
    """Resolve a bundled resource, working both from source and from a
    PyInstaller --onefile exe (where data files unpack to sys._MEIPASS)."""
    base = getattr(sys, "_MEIPASS", None)  # type: ignore[attr-defined]
    if not base:
        base = os.path.abspath(".")
    return os.path.join(base, rel)


def app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(".")


TEMPLATE_PATH = resource_path("template.docx")
LOG_PATH = os.path.join(app_dir(), "app.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.handlers.RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=2),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("defaulter_app.ui")

DEFAULT_SUBJECTS = [
    ("T1", "Design of Experiments (DOE)", "Theory"),
    ("T2", "Logistics and Supply Chain Management (LSCM)", "Theory"),
    ("T3", "Power Plant Engineering (PPE)", "Theory"),
    ("T4", "AIML", "Theory"),
    ("P1", "DOE", "Practical"),
    ("P2", "PPE", "Practical"),
]


def to_float(value: Any) -> Optional[float]:
    """Safe float conversion for openpyxl cell values."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe(fn):
    """Decorator: log the full traceback, show a friendly message box."""
    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except Exception as e:
            log.exception("Error in %s", fn.__name__)
            messagebox.showerror("Something went wrong", str(e))
    return wrapper


def _show_modal(win: "ctk.CTkToplevel") -> None:
    """Make a Toplevel modal safely.

    grab_set() requires the window to already be viewable (mapped by the
    window manager). Calling it immediately after creating the window is
    racy - on some window managers / after a previous grab-holding window
    has just closed, the new window isn't mapped yet and grab_set() raises
    'TclError: grab failed: window not viewable'. wait_visibility() blocks
    until the window actually receives a Visibility event, which makes the
    following grab_set() reliable.
    """
    win.transient(cast("ctk.CTk", win.master))
    win.wait_visibility()
    win.grab_set()
    win.focus_force()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Defaulter Letter Generator")
        self.geometry("1050x820")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.faculty_name = ctk.StringVar(value="Prof. Faculty Name")

        # Header
        header = ctk.CTkFrame(self, height=60)
        header.pack(fill="x", padx=10, pady=(10, 0))
        ctk.CTkLabel(header, text="Faculty Name:",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=(10, 6))
        ctk.CTkEntry(header, textvariable=self.faculty_name, width=280).pack(side="left")
        ctk.CTkLabel(header, text="Defaulter Threshold (%):").pack(side="left", padx=(20, 6))
        self.threshold = ctk.CTkEntry(header, width=60)
        self.threshold.insert(0, "75")
        self.threshold.bind("<Return>", lambda e: self.refresh_attendance_table())
        self.threshold.bind("<FocusOut>", lambda e: self.refresh_attendance_table())
        self.threshold.pack(side="left")

        # Tabs
        self.tabs = ctk.CTkTabview(self, width=1000, height=700)
        self.tabs.pack(padx=10, pady=10, fill="both", expand=True)

        self.tab_students = self.tabs.add("Students")
        self.tab_subjects = self.tabs.add("Subjects")
        self.tab_attendance = self.tabs.add("Attendance")
        self.tab_generate = self.tabs.add("Generate Letters")
        self.tab_history = self.tabs.add("History")

        self.build_students_tab()
        self.build_subjects_tab()
        self.build_attendance_tab()
        self.build_generate_tab()
        self.build_history_tab()

        database.init_db()
        if not database.fetch_all_subjects():
            self.seed_default_subjects()
        self.refresh_students()
        self.refresh_subjects()
        self.refresh_attendance_table()
        self.refresh_history()

    def get_threshold(self) -> float:
        try:
            return float(self.threshold.get())
        except ValueError:
            return 75.0

    def seed_default_subjects(self):
        existing = {s["code"] for s in database.fetch_all_subjects()}
        for code, name, stype in DEFAULT_SUBJECTS:
            if code not in existing:
                database.add_subject(code, name, stype)

    # ============================================================ STUDENTS
    def build_students_tab(self):
        top = ctk.CTkFrame(self.tab_students, fg_color="transparent")
        top.pack(fill="x", pady=5)

        ctk.CTkButton(top, text="Import Students Excel",
                      command=self.import_students_excel, width=180).pack(side="left", padx=5)
        ctk.CTkButton(top, text="Export Template",
                      command=self.export_student_template, width=150,
                      fg_color="gray40").pack(side="left", padx=5)
        ctk.CTkButton(top, text="Add Manually",
                      command=self.open_add_student, width=140,
                      fg_color="green").pack(side="left", padx=5)

        self.student_search = ctk.CTkEntry(top, placeholder_text="Search roll no / name...", width=220)
        self.student_search.pack(side="left", padx=(20, 5))
        self.student_search.bind("<KeyRelease>", lambda e: self.refresh_students())

        cols = ("id", "roll_no", "student_name", "class", "div",
                "parent_name", "parent_contact")
        self.student_tree = ttk.Treeview(self.tab_students, columns=cols,
                                          show="headings", height=18)
        headings = ["ID", "Roll No", "Name", "Class", "Div", "Parent", "Contact"]
        for c, h in zip(cols, headings):
            self.student_tree.heading(c, text=h)
            self.student_tree.column(c, width=120, anchor="center")
        self.student_tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.student_tree.bind("<Double-1>", lambda e: self.open_add_student(edit_selected=True))

        bot = ctk.CTkFrame(self.tab_students, fg_color="transparent")
        bot.pack(fill="x", pady=5)
        ctk.CTkButton(bot, text="Delete Selected",
                      command=self.delete_selected_student,
                      fg_color="darkred").pack(side="left", padx=5)

    def refresh_students(self):
        for i in self.student_tree.get_children():
            self.student_tree.delete(i)
        kw = self.student_search.get().strip() if hasattr(self, "student_search") else ""
        rows = database.search_students(kw) if kw else database.fetch_all_students()
        for r in rows:
            self.student_tree.insert("", "end", values=(
                r["id"], r["roll_no"], r["student_name"],
                r["class"], r["div"], r["parent_name"], r["parent_contact"]
            ))

    @_safe
    def import_students_excel(self):
        path = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx")])
        if not path:
            return
        wb = load_workbook(path)
        ws: Optional[Worksheet] = wb.active
        if ws is None:
            messagebox.showerror("Error", "No active sheet found.")
            return
        count, skipped = 0, 0
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or row[0] is None:
                continue
            roll = str(row[0]).strip()
            name = str(row[1]).strip() if len(row) > 1 and row[1] else ""
            if not roll or not name:
                skipped += 1
                continue
            data = {
                "roll_no": roll,
                "student_name": name,
                "class": str(row[2]).strip() if len(row) > 2 and row[2] else "",
                "div": str(row[3]).strip() if len(row) > 3 and row[3] else "",
                "parent_name": str(row[4]).strip() if len(row) > 4 and row[4] else "",
                "parent_contact": str(row[5]).strip() if len(row) > 5 and row[5] else "",
            }
            database.upsert_student(data)
            count += 1
        self.refresh_students()
        self.refresh_attendance_table()
        msg = f"{count} students imported/updated."
        if skipped:
            msg += f"\n{skipped} row(s) skipped (missing roll no / name)."
        messagebox.showinfo("Imported", msg)

    def export_student_template(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                             initialfile="students_template.xlsx")
        if not path:
            return
        wb = Workbook()
        ws = wb.active
        if ws is None:
            return
        ws.append(["Roll No", "Student Name", "Class", "Div",
                   "Parent Name", "Parent Contact"])
        ws.append(["101", "Rohan Sharma", "BE/Mechanical", "A",
                   "Mr. Sharma", "9876543210"])
        wb.save(path)
        messagebox.showinfo("Saved", f"Template saved: {path}")

    def open_add_student(self, edit_selected: bool = False):
        existing_row: dict[str, Any] | None = None
        if edit_selected:
            sel = self.student_tree.selection()
            if not sel:
                return
            values = self.student_tree.item(sel[0])["values"]
            existing_row = dict(zip(
                ("id", "roll_no", "student_name", "class", "div",
                 "parent_name", "parent_contact"), values))

        win = ctk.CTkToplevel(self)
        win.title("Edit Student" if existing_row else "Add Student")
        win.geometry("460x620")
        win.resizable(False, False)
        win.update_idletasks()
        x = (win.winfo_screenwidth() // 2) - 230
        y = (win.winfo_screenheight() // 2) - 310
        win.geometry(f"460x620+{x}+{y}")
        _show_modal(win)

        ctk.CTkLabel(win, text=win.title(),
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(15, 10))

        fields = {}
        labels = [
            ("roll_no", "Roll No *"),
            ("student_name", "Name *"),
            ("class", "Class"),
            ("div", "Div"),
            ("parent_name", "Parent Name"),
            ("parent_contact", "Parent Contact"),
        ]
        for key, label in labels:
            ctk.CTkLabel(win, text=label, anchor="w", width=340).pack(pady=(6, 0))
            e = ctk.CTkEntry(win, width=340)
            if existing_row:
                e.insert(0, str(existing_row.get(key, "")))
            e.pack(pady=(0, 4))
            fields[key] = e
        fields["roll_no"].focus_set()

        @_safe
        def save(_self=self):
            data = {k: v.get().strip() for k, v in fields.items()}
            if not data["roll_no"] or not data["student_name"]:
                messagebox.showwarning("Missing", "Roll No and Name required.")
                return
            if existing_row:
                database.update_student(int(existing_row["id"]), data)
            else:
                database.upsert_student(data)
            self.refresh_students()
            self.refresh_attendance_table()
            win.destroy()

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="Save", width=140, command=save).grid(row=0, column=0, padx=8)
        ctk.CTkButton(btn_frame, text="Cancel", width=100, fg_color="gray40",
                      command=win.destroy).grid(row=0, column=1, padx=8)
        win.bind("<Return>", lambda e: save())

    def delete_selected_student(self):
        sel = self.student_tree.selection()
        if not sel:
            return
        sid = int(self.student_tree.item(sel[0])["values"][0])
        if messagebox.askyesno("Delete", f"Delete student #{sid}? This also removes their attendance."):
            database.delete_student(sid)
            self.refresh_students()
            self.refresh_attendance_table()

    # ============================================================ SUBJECTS
    def build_subjects_tab(self):
        form = ctk.CTkFrame(self.tab_subjects)
        form.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(form, text="Subject ID:",
                     font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=6, pady=6, sticky="e")
        self.subj_id = ctk.CTkEntry(form, width=70, placeholder_text="auto")
        self.subj_id.grid(row=0, column=1, padx=6, pady=6)
        self.subj_id.configure(state="disabled")

        ctk.CTkLabel(form, text="Code:",
                     font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=6, pady=6, sticky="e")
        self.subj_code = ctk.CTkEntry(form, width=100, placeholder_text="T1 / P1")
        self.subj_code.grid(row=0, column=3, padx=6, pady=6)

        ctk.CTkLabel(form, text="Name:",
                     font=ctk.CTkFont(weight="bold")).grid(row=0, column=4, padx=6, pady=6, sticky="e")
        self.subj_name = ctk.CTkEntry(form, width=320, placeholder_text="Design of Experiments (DOE)")
        self.subj_name.grid(row=0, column=5, padx=6, pady=6)

        ctk.CTkLabel(form, text="Type:",
                     font=ctk.CTkFont(weight="bold")).grid(row=0, column=6, padx=6, pady=6, sticky="e")
        self.subj_type = ctk.CTkOptionMenu(form, values=["Theory", "Practical"], width=120)
        self.subj_type.grid(row=0, column=7, padx=6, pady=6)

        btns = ctk.CTkFrame(self.tab_subjects, fg_color="transparent")
        btns.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(btns, text="Add", width=120, fg_color="green",
                      command=self.add_subject).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Update (by ID)", width=160,
                      command=self.update_subject).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Delete Selected", width=160, fg_color="darkred",
                      command=self.delete_subject).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Clear Form", width=120, fg_color="gray40",
                      command=self.clear_subject_form).pack(side="left", padx=4)

        cols = ("id", "code", "name", "type")
        self.subj_tree = ttk.Treeview(self.tab_subjects, columns=cols, show="headings", height=16)
        for c, h, w in zip(cols, ["ID", "Code", "Name", "Type"], [60, 100, 500, 120]):
            self.subj_tree.heading(c, text=h)
            self.subj_tree.column(c, width=w, anchor="center")
        self.subj_tree.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        self.subj_tree.bind("<Double-1>", lambda e: self.load_subject_into_form())

    def clear_subject_form(self):
        self.subj_id.configure(state="normal")
        self.subj_id.delete(0, "end")
        self.subj_id.configure(state="disabled")
        self.subj_code.delete(0, "end")
        self.subj_name.delete(0, "end")
        self.subj_type.set("Theory")

    def load_subject_into_form(self):
        sel = self.subj_tree.selection()
        if not sel:
            return
        values = self.subj_tree.item(sel[0])["values"]
        self.subj_id.configure(state="normal")
        self.subj_id.delete(0, "end")
        self.subj_id.insert(0, str(values[0]))
        self.subj_id.configure(state="disabled")
        self.subj_code.delete(0, "end")
        self.subj_code.insert(0, str(values[1]))
        self.subj_name.delete(0, "end")
        self.subj_name.insert(0, str(values[2]))
        self.subj_type.set(str(values[3]))

    @_safe
    def add_subject(self):
        code = self.subj_code.get().strip()
        name = self.subj_name.get().strip()
        stype = self.subj_type.get()
        if not code or not name:
            messagebox.showwarning("Missing", "Code and Name are required.")
            return
        database.add_subject(code, name, stype)
        self.refresh_subjects()
        self.refresh_attendance_table()
        self.clear_subject_form()

    @_safe
    def update_subject(self):
        sid_txt = self.subj_id.get().strip()
        if not sid_txt:
            messagebox.showwarning("Missing ID",
                                    "Select a subject from the table first "
                                    "(or double-click it), then edit and click Update.")
            return
        sid = int(sid_txt)
        code = self.subj_code.get().strip()
        name = self.subj_name.get().strip()
        stype = self.subj_type.get()
        if not code or not name:
            messagebox.showwarning("Missing", "Code and Name are required.")
            return
        database.update_subject(sid, code, name, stype)
        self.refresh_subjects()
        self.refresh_attendance_table()
        self.clear_subject_form()

    def refresh_subjects(self):
        for i in self.subj_tree.get_children():
            self.subj_tree.delete(i)
        for r in database.fetch_all_subjects():
            self.subj_tree.insert("", "end", values=(r["id"], r["code"], r["name"], r["type"]))

    def delete_subject(self):
        sel = self.subj_tree.selection()
        if not sel:
            messagebox.showinfo("No Selection", "Select a subject from the table first.")
            return
        sid = int(self.subj_tree.item(sel[0])["values"][0])
        code = self.subj_tree.item(sel[0])["values"][1]
        if not messagebox.askyesno("Confirm Delete",
                                    f"Delete subject #{sid} ({code})?\n"
                                    "Existing attendance records for it are kept."):
            return
        database.delete_subject(sid)
        self.refresh_subjects()
        self.refresh_attendance_table()
        self.clear_subject_form()

    # ========================================================== ATTENDANCE
    def build_attendance_tab(self):
        top = ctk.CTkFrame(self.tab_attendance, fg_color="transparent")
        top.pack(fill="x", pady=5)
        ctk.CTkButton(top, text="Upload Attendance Excel",
                      command=self.import_attendance_excel, width=200).pack(side="left", padx=5)
        ctk.CTkButton(top, text="Export Template",
                      command=self.export_attendance_template, width=150,
                      fg_color="gray40").pack(side="left", padx=5)
        ctk.CTkButton(top, text="Add / Edit Attendance", command=self.open_edit_attendance,
                      width=180, fg_color="green").pack(side="left", padx=5)
        ctk.CTkLabel(top, text="(double-click a row to edit that student)",
                     text_color="gray50").pack(side="left", padx=10)

        # Columns are rebuilt dynamically in refresh_attendance_table() since
        # the subject list can change.
        self.att_tree = ttk.Treeview(self.tab_attendance, show="headings", height=18)
        self.att_tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.att_tree.bind("<Double-1>", lambda e: self.open_edit_attendance())

        style = ttk.Style()
        self.att_tree.tag_configure("defaulter", foreground="#c0392b")
        self.att_tree.tag_configure("ok", foreground="#1e8449")

    def refresh_attendance_table(self):
        if not hasattr(self, "att_tree"):
            return
        threshold = self.get_threshold()
        subjects = database.fetch_all_subjects()
        codes = [s["code"] for s in subjects]

        cols = ("roll_no", "student_name", "overall_theory", *codes)
        self.att_tree["columns"] = cols
        self.att_tree.heading("roll_no", text="Roll No")
        self.att_tree.heading("student_name", text="Student Name")
        self.att_tree.heading("overall_theory", text="Overall Theory %")
        self.att_tree.column("roll_no", width=100, anchor="center")
        self.att_tree.column("student_name", width=200, anchor="w")
        self.att_tree.column("overall_theory", width=125, anchor="center")
        for code in codes:
            self.att_tree.heading(code, text=code)
            self.att_tree.column(code, width=70, anchor="center")

        for i in self.att_tree.get_children():
            self.att_tree.delete(i)

        for entry in database.get_attendance_matrix():
            att = entry["attendance"]
            overall = entry["overall_theory"]
            row_vals = [entry["roll_no"], entry["student_name"],
                        "-" if overall is None else f"{overall:.1f}"]
            is_defaulter = overall is not None and overall < threshold
            for code in codes:
                value = att.get(code)
                if value is None or value["percent"] is None:
                    row_vals.append("-")
                else:
                    row_vals.append(f"{value['percent']:g}")
            tag = "defaulter" if is_defaulter else "ok"
            self.att_tree.insert("", "end", iid=str(entry["id"]),
                                  values=row_vals, tags=(tag,))

    @_safe
    def import_attendance_excel(self):
        path = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx")])
        if not path:
            return
        wb = load_workbook(path)
        ws: Optional[Worksheet] = wb.active
        if ws is None:
            messagebox.showerror("Error", "No active sheet found.")
            return

        headers = [str(c.value).strip() if c.value else "" for c in ws[1]]
        # Expected: Roll No | Student Name | T1 Present | T1 Lectures | ...
        subject_cols = {}
        for i in range(2, len(headers) - 1, 2):
            code = headers[i].removesuffix(" Present").strip()
            if code and headers[i + 1].lower().endswith("lectures"):
                subject_cols[i] = (code, i + 1)

        count, not_found = 0, 0
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or row[0] is None:
                continue
            roll = str(row[0]).strip()
            student = database.get_student_by_roll(roll)
            if not student:
                not_found += 1
                continue
            for present_idx, (code, lectures_idx) in subject_cols.items():
                if lectures_idx < len(row):
                    attended = to_float(row[present_idx])
                    lectures = to_float(row[lectures_idx])
                    if attended is not None and lectures is not None:
                        database.set_attendance_lectures(
                            student["id"], code, int(attended), int(lectures)
                        )
            count += 1
        self.refresh_attendance_table()
        msg = f"Attendance updated for {count} students."
        if not_found:
            msg += f"\n{not_found} row(s) skipped (roll no not found - add the student first)."
        messagebox.showinfo("Imported", msg)

    def export_attendance_template(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                             initialfile="attendance_template.xlsx")
        if not path:
            return
        wb = Workbook()
        ws = wb.active
        if ws is None:
            return
        subs = [s["code"] for s in database.fetch_all_subjects()]
        ws.append(["Roll No", "Student Name"] + [
            item for code in subs for item in (f"{code} Present", f"{code} Lectures")
        ])
        for s in database.fetch_all_students():
            current = {a["subject_code"]: a for a in database.get_attendance(s["id"])}
            values = []
            for code in subs:
                row = current.get(code)
                values.extend([row["attended"] if row else "",
                               row["lectures"] if row else ""])
            ws.append([s["roll_no"], s["student_name"]] + values)
        wb.save(path)
        messagebox.showinfo("Saved", f"Template saved: {path}")

    def open_edit_attendance(self):
        """Manual entry: pick a student (if none selected, ask first), then
        show one editable field per subject, pre-filled with the current
        percentage, and save them all in one go."""
        sel = self.att_tree.selection()
        if sel:
            student_id = int(sel[0])
            student = database.get_student(student_id)
        else:
            student = self._prompt_pick_student()
            if student is None:
                return
            student_id = student["id"]

        subjects = database.fetch_all_subjects()
        if not subjects:
            messagebox.showinfo("No Subjects", "Add a subject first (Subjects tab).")
            return
        current = {a["subject_code"]: a for a in database.get_attendance(student_id)}

        win = ctk.CTkToplevel(self)
        win.title(f"Attendance — {student['student_name']} ({student['roll_no']})")
        win.geometry("520x" + str(140 + 46 * len(subjects) + 80))
        win.resizable(False, False)
        _show_modal(win)

        ctk.CTkLabel(win, text=f"{student['student_name']}  (Roll {student['roll_no']})",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 5))
        ctk.CTkLabel(win, text="Enter attended lectures and total lectures (blank = leave unset)",
                     text_color="gray50").pack(pady=(0, 10))

        entries: dict[str, tuple[ctk.CTkEntry, ctk.CTkEntry]] = {}
        for s in subjects:
            row = ctk.CTkFrame(win, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=4)
            ctk.CTkLabel(row, text=f"{s['code']} - {s['name']}", width=230, anchor="w").pack(side="left")
            attended = ctk.CTkEntry(row, width=80, placeholder_text="Present")
            lectures = ctk.CTkEntry(row, width=80, placeholder_text="Lectures")
            old = current.get(s["code"])
            if old and old["attended"] is not None:
                attended.insert(0, str(old["attended"]))
            if old and old["lectures"] is not None:
                lectures.insert(0, str(old["lectures"]))
            attended.pack(side="left", padx=(0, 5))
            lectures.pack(side="left")
            entries[s["code"]] = (attended, lectures)

        @_safe
        def save(_self=self):
            values = {}
            for code, (attended_entry, lectures_entry) in entries.items():
                attended_text = attended_entry.get().strip()
                lectures_text = lectures_entry.get().strip()
                if attended_text == "" and lectures_text == "":
                    continue
                try:
                    attended = int(attended_text)
                    lectures = int(lectures_text)
                except ValueError:
                    messagebox.showwarning("Invalid value", f"Enter whole lecture counts for {code}.")
                    return
                if lectures <= 0 or attended < 0 or attended > lectures:
                    messagebox.showwarning("Invalid value", f"{code}: present must be between 0 and total lectures.")
                    return
                values[code] = (attended, lectures)
            database.set_attendance_bulk(student_id, values)
            self.refresh_attendance_table()
            win.destroy()

        btns = ctk.CTkFrame(win, fg_color="transparent")
        btns.pack(pady=15)
        ctk.CTkButton(btns, text="Save", width=140, command=save).grid(row=0, column=0, padx=8)
        ctk.CTkButton(btns, text="Cancel", width=100, fg_color="gray40",
                      command=win.destroy).grid(row=0, column=1, padx=8)
        win.bind("<Return>", lambda e: save())

    def _prompt_pick_student(self):
        """Small dialog to choose a student by roll no when none is
        selected in the attendance table."""
        students = database.fetch_all_students()
        if not students:
            messagebox.showinfo("No Students", "Add a student first (Students tab).")
            return None

        win = ctk.CTkToplevel(self)
        win.title("Choose Student")
        win.geometry("360x160")
        win.resizable(False, False)
        _show_modal(win)

        ctk.CTkLabel(win, text="Roll No:").pack(pady=(20, 4))
        options = [f"{s['roll_no']} - {s['student_name']}" for s in students]
        picked = ctk.StringVar(value=options[0])
        ctk.CTkOptionMenu(win, values=options, variable=picked, width=280).pack()

        result = {"student": None}

        def confirm():
            roll = picked.get().split(" - ")[0]
            result["student"] = database.get_student_by_roll(roll)
            win.destroy()

        ctk.CTkButton(win, text="Continue", command=confirm).pack(pady=20)
        win.wait_window()
        return result["student"]

    # =========================================================== GENERATE
    def build_generate_tab(self):
        ctk.CTkLabel(self.tab_generate,
                     text="Generate Defaulter Letters (PDF)",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)

        self.gen_info = ctk.CTkLabel(self.tab_generate, text="")
        self.gen_info.pack(pady=5)

        ctk.CTkButton(self.tab_generate, text="Refresh Defaulter List",
                      command=self.refresh_defaulters, width=200).pack(pady=5)

        cols = ("roll_no", "student_name", "min_pct", "status")
        self.def_tree = ttk.Treeview(self.tab_generate, columns=cols, show="headings", height=14)
        for c, h in zip(cols, ["Roll No", "Name", "Min %", "Status"]):
            self.def_tree.heading(c, text=h)
            self.def_tree.column(c, width=180, anchor="center")
        self.def_tree.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(self.tab_generate, text="Letter info (used for all generated letters):").pack(pady=(10, 0))

        info = ctk.CTkFrame(self.tab_generate, fg_color="transparent")
        info.pack(pady=5)
        self.date_e = self._mk(info, "Date", datetime.date.today().strftime("%d/%m/%Y"))
        self.intim_e = self._mk(info, "Intimation No")
        self.from_e = self._mk(info, "From Date")
        self.to_e = self._mk(info, "To Date")

        ctk.CTkButton(self.tab_generate, text="Generate All PDFs",
                      command=self.generate_all_pdfs, width=220,
                      fg_color="green").pack(pady=15)

    def _mk(self, parent, label, default=""):
        ctk.CTkLabel(parent, text=label, width=100).pack(side="left", padx=5)
        e = ctk.CTkEntry(parent, width=140)
        e.pack(side="left", padx=5)
        if default:
            e.insert(0, default)
        return e

    def refresh_defaulters(self):
        threshold = self.get_threshold()
        for i in self.def_tree.get_children():
            self.def_tree.delete(i)
        rows = database.list_defaulters(threshold)
        for s in rows:
            matrix = next(
                entry for entry in database.get_attendance_matrix()
                if entry["id"] == s["id"]
            )
            overall = matrix["overall_theory"] or 0
            self.def_tree.insert("", "end", values=(
                s["roll_no"], s["student_name"], f"{overall:.1f}", "Defaulter"
            ))
        self.gen_info.configure(text=f"{len(rows)} defaulters found (<{threshold}%)")

    @_safe
    def generate_all_pdfs(self):
        if not os.path.exists(TEMPLATE_PATH):
            messagebox.showerror(
                "Template Missing",
                f"letter template not found at:\n{TEMPLATE_PATH}\n\n"
                "Place your template.docx next to the app (or in the exe's data folder).")
            return

        threshold = self.get_threshold()
        defaulters = database.list_defaulters(threshold)
        if not defaulters:
            messagebox.showinfo("None", "No defaulters found.")
            return

        out_dir = filedialog.askdirectory(title="Choose output folder for PDFs")
        if not out_dir:
            return

        subjects = [dict(s) for s in database.fetch_all_subjects()]
        date = self.date_e.get().strip()
        intim = self.intim_e.get().strip()
        from_d = self.from_e.get().strip()
        to_d = self.to_e.get().strip()
        faculty = self.faculty_name.get().strip()

        ok, fail, failures = 0, 0, []
        for s in defaulters:
            try:
                att = {a["subject_code"]: a["percent"] for a in database.get_attendance(s["id"])}
                data = {
                    "date": date,
                    "class": s["class"] or "",
                    "div": s["div"] or "",
                    "roll_no": s["roll_no"],
                    "student_name": s["student_name"],
                    "parent_name": s["parent_name"] or "",
                    "intimation_no": intim,
                    "from_date": from_d,
                    "to_date": to_d,
                    "faculty_name": faculty,
                }

                tmp_docx = os.path.join(tempfile.gettempdir(), f"letter_{s['roll_no']}.docx")
                pdf_utils.fill_template(TEMPLATE_PATH, data, subjects, att, tmp_docx)

                pdf_path = os.path.join(out_dir, f"Defaulter_Letter_{s['roll_no']}.pdf")
                result = pdf_utils.docx_to_pdf(tmp_docx, pdf_path)
                if result and os.path.exists(result):
                    ok += 1
                else:
                    fail += 1
                    failures.append(s["roll_no"])

                data["student_id"] = s["id"]
                database.insert_letter(data)

            except Exception as e:
                log.exception("Letter generation failed for %s", s["roll_no"])
                fail += 1
                failures.append(s["roll_no"])

        self.refresh_history()
        msg = f"Generated: {ok}\nFailed: {fail}\nFolder: {out_dir}"
        if failures:
            msg += f"\nFailed roll numbers: {', '.join(failures)}\n(see app.log for details)"
        messagebox.showinfo("Done", msg)

    # ============================================================ HISTORY
    def build_history_tab(self):
        cols = ("id", "date", "roll_no", "student_name", "faculty_name", "created_at")
        self.hist_tree = ttk.Treeview(self.tab_history, columns=cols, show="headings", height=20)
        for c, h in zip(cols, ["ID", "Date", "Roll No", "Name", "Faculty", "Saved At"]):
            self.hist_tree.heading(c, text=h)
            self.hist_tree.column(c, width=150, anchor="center")
        self.hist_tree.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkButton(self.tab_history, text="Delete Selected",
                      fg_color="darkred", command=self.delete_history).pack(pady=5)

    def refresh_history(self):
        for i in self.hist_tree.get_children():
            self.hist_tree.delete(i)
        for r in database.fetch_all_letters():
            self.hist_tree.insert("", "end", values=(
                r["id"], r["date"], r["roll_no"], r["student_name"],
                r["faculty_name"], r["created_at"]
            ))

    def delete_history(self):
        sel = self.hist_tree.selection()
        if not sel:
            return
        letter_id = int(self.hist_tree.item(sel[0])["values"][0])
        if messagebox.askyesno("Delete", f"Delete letter record #{letter_id}?"):
            database.delete_letter(letter_id)
            self.refresh_history()


if __name__ == "__main__":
    try:
        app = App()
        app.mainloop()
    except Exception:
        logging.getLogger("defaulter_app.ui").exception("Fatal startup error")
        raise