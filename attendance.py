"""
attendance.py - Attendance Logic, Reporting, and Export Module
Handles business logic for attendance management, duplicate checks,
and generating CSV and professional Excel (.xlsx) reports directly using openpyxl.
"""

import io
import csv
from datetime import datetime, date, timedelta
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import database

def get_report_data(report_type='all', date_filter=None, department=None, year=None, student_id=None):
    """
    Fetches filtered attendance dataset based on timeframe or criteria.
    report_type: 'daily', 'weekly', 'monthly', or 'all'
    """
    today = date.today()
    start_date = None
    end_date = today.isoformat()

    if report_type == 'daily':
        start_date = date_filter if date_filter else today.isoformat()
        end_date = start_date
    elif report_type == 'weekly':
        start_date = (today - timedelta(days=7)).isoformat()
    elif report_type == 'monthly':
        start_date = (today - timedelta(days=30)).isoformat()

    conn = database.get_db_connection()
    query = """
    SELECT 
        a.id as attendance_id,
        a.date,
        a.time,
        a.status,
        a.verification_mode,
        a.confidence_score,
        a.notes,
        s.id as student_id,
        s.roll_number,
        s.name as student_name,
        s.department,
        s.year,
        s.email,
        s.phone
    FROM attendance a
    JOIN students s ON a.student_id = s.id
    WHERE 1=1
    """
    params = []

    if start_date and end_date:
        if start_date == end_date:
            query += " AND a.date = ?"
            params.append(start_date)
        else:
            query += " AND a.date BETWEEN ? AND ?"
            params.extend([start_date, end_date])

    if department and department != 'All':
        query += " AND s.department = ?"
        params.append(department)

    if year and year != 'All':
        query += " AND s.year = ?"
        params.append(year)

    if student_id:
        query += " AND s.id = ?"
        params.append(student_id)

    query += " ORDER BY a.date DESC, a.time DESC"
    records = conn.execute(query, params).fetchall()
    conn.close()

    return [dict(r) for r in records]

def export_attendance_csv(records):
    """
    Generates a CSV byte string from attendance records.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Professional CSV Headers
    headers = [
        "Record ID", "Date", "Time", "Roll Number", "Student Name",
        "Department", "Year", "Status", "Verification Mode",
        "Confidence (%)", "Notes"
    ]
    writer.writerow(headers)

    for r in records:
        writer.writerow([
            r.get('attendance_id', ''),
            r.get('date', ''),
            r.get('time', ''),
            r.get('roll_number', ''),
            r.get('student_name', ''),
            r.get('department', ''),
            r.get('year', ''),
            r.get('status', ''),
            r.get('verification_mode', ''),
            f"{r.get('confidence_score', 0):.1f}%" if r.get('confidence_score') else 'N/A',
            r.get('notes', '')
        ])

    output.seek(0)
    return output.getvalue().encode('utf-8-sig')

def export_attendance_excel(records, sheet_title="Attendance Report"):
    """
    Generates a beautifully styled, commercial-grade Excel (.xlsx) file using openpyxl.
    Features:
    - Navy blue header styling with white bold text
    - Status-colored pills (Present = soft green, Late = soft orange, Absent = soft red)
    - Auto-column widths and thin border gridlines
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_title[:30]
    ws.views.sheetView[0].showGridLines = True

    # 1. Title Banner
    ws.merge_cells('A1:K1')
    title_cell = ws['A1']
    title_cell.value = f"STUDENT ATTENDANCE DETAILED REPORT — {datetime.now().strftime('%d %B %Y')}"
    title_cell.font = Font(name='Segoe UI', size=14, bold=True, color='FFFFFF')
    title_cell.fill = PatternFill(start_color='0F172A', end_color='0F172A', fill_type='solid') # Navy
    title_cell.alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 36

    # 2. Table Column Headers
    headers = [
        "Record ID", "Date", "Time", "Roll Number", "Student Name",
        "Department", "Year", "Status", "Verification Mode",
        "Confidence", "Notes"
    ]
    
    header_fill = PatternFill(start_color='1E3A8A', end_color='1E3A8A', fill_type='solid') # Dark Blue
    header_font = Font(name='Segoe UI', size=11, bold=True, color='FFFFFF')
    header_align = Alignment(horizontal='center', vertical='center', wrap_text=True)

    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    ws.row_dimensions[2].height = 28

    # 3. Status Fill colors
    present_fill = PatternFill(start_color='DCFCE7', end_color='DCFCE7', fill_type='solid') # Light green
    late_fill = PatternFill(start_color='FEF3C7', end_color='FEF3C7', fill_type='solid') # Light amber
    absent_fill = PatternFill(start_color='FEE2E2', end_color='FEE2E2', fill_type='solid') # Light red
    zebra_fill = PatternFill(start_color='F8FAFC', end_color='F8FAFC', fill_type='solid')

    row_font = Font(name='Segoe UI', size=10)
    bold_font = Font(name='Segoe UI', size=10, bold=True)

    # 4. Populate rows
    for row_idx, r in enumerate(records, start=3):
        status = r.get('status', '')
        conf = f"{r.get('confidence_score', 0):.1f}%" if r.get('confidence_score') else "N/A"
        
        row_data = [
            r.get('attendance_id', ''),
            r.get('date', ''),
            r.get('time', ''),
            r.get('roll_number', ''),
            r.get('student_name', ''),
            r.get('department', ''),
            r.get('year', ''),
            status,
            r.get('verification_mode', ''),
            conf,
            r.get('notes', '')
        ]

        is_even = (row_idx % 2 == 0)

        for col_idx, val in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = row_font
            cell.border = thin_border
            cell.alignment = Alignment(vertical='center')

            if col_idx in (1, 2, 3, 4, 7, 9, 10):
                cell.alignment = Alignment(horizontal='center', vertical='center')

            # Highlight status column
            if col_idx == 8:
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.font = bold_font
                if status == 'Present':
                    cell.fill = present_fill
                elif status == 'Late':
                    cell.fill = late_fill
                elif status == 'Absent':
                    cell.fill = absent_fill
            elif is_even:
                cell.fill = zebra_fill

        ws.row_dimensions[row_idx].height = 22

    # 5. Auto-fit column widths
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = 0
        for cell in col:
            # Skip title row from width calculation
            if cell.row == 1:
                continue
            val_str = str(cell.value or '')
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    # Save to memory buffer
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()

def mark_bulk_manual_attendance(student_ids, status, att_date=None, notes="Admin bulk update"):
    """Marks or updates attendance for multiple students simultaneously."""
    today_str = att_date if att_date else date.today().isoformat()
    now_time = datetime.now().strftime("%H:%M:%S")
    results = {'success': 0, 'skipped': 0, 'errors': []}

    for sid in student_ids:
        student = database.get_student_by_id(sid)
        if not student:
            continue
        
        ok, msg, rec = database.mark_attendance(
            student_id=sid,
            roll_number=student['roll_number'],
            status=status,
            verification_mode='Manual',
            confidence_score=100.0,
            notes=notes,
            att_date=today_str,
            att_time=now_time
        )
        if ok:
            results['success'] += 1
        else:
            results['skipped'] += 1

    return results
