"""CSV / Excel export helpers for attendance reports."""
import io
import pandas as pd


def _attendance_to_dataframe(records) -> pd.DataFrame:
    rows = []
    for r in records:
        rows.append({
            "Roll Number": r.student.roll_number,
            "Name": r.student.name,
            "Department": r.student.department,
            "Year": r.student.year,
            "Section": r.student.section,
            "Subject": r.subject.name if r.subject else "-",
            "Date": r.date.isoformat(),
            "Time": r.time.strftime("%H:%M:%S"),
            "Status": r.status,
        })
    return pd.DataFrame(rows)


def export_to_csv(records) -> io.BytesIO:
    df = _attendance_to_dataframe(records)
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return buf


def export_to_excel(records) -> io.BytesIO:
    df = _attendance_to_dataframe(records)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Attendance")
    buf.seek(0)
    return buf
