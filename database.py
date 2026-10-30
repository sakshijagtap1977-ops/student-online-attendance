"""
database.py - Database Connection and CRUD Operations
Handles SQLite connection, schema definition, seed initialization,
and database operations for the Student Online Attendance Detection System.
"""

import sqlite3
import os
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'attendance.db')

def get_db_connection():
    """Returns a SQLite connection with Row factory enabled for dictionary access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Initializes database schema and populates default admin and sample data if needed."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Admin users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 2. Students table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_number TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        department TEXT NOT NULL,
        year TEXT NOT NULL,
        gender TEXT DEFAULT 'Other',
        phone TEXT DEFAULT '',
        photo_path TEXT DEFAULT '',
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 3. Student login credentials table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_credentials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        roll_number TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )
    """)

    # 4. Face encodings & photos table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS face_encodings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        roll_number TEXT NOT NULL,
        image_path TEXT NOT NULL,
        encoding_blob BLOB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )
    """)

    # 5. Attendance records table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        roll_number TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('Present', 'Absent', 'Late')),
        verification_mode TEXT DEFAULT 'Face Recognition',
        confidence_score REAL DEFAULT 0.0,
        notes TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(student_id, date),
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )
    """)

    # 6. Subjects table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        department TEXT NOT NULL,
        semester TEXT NOT NULL
    )
    """)

    # Check and insert default admin
    cursor.execute("SELECT id FROM admins WHERE username = ?", ('admin',))
    if not cursor.fetchone():
        hashed_pw = generate_password_hash('admin123')
        cursor.execute("""
        INSERT INTO admins (username, password_hash, full_name, email)
        VALUES (?, ?, ?, ?)
        """, ('admin', hashed_pw, 'System Administrator', 'admin@attendify.edu'))

    # Check and insert default subjects
    cursor.execute("SELECT COUNT(*) as count FROM subjects")
    if cursor.fetchone()['count'] == 0:
        subjects_data = [
            ('CS101', 'Artificial Intelligence & Machine Learning', 'Computer Science', 'Semester 5'),
            ('CS102', 'Computer Vision & Pattern Recognition', 'Computer Science', 'Semester 5'),
            ('CS103', 'Database Management Systems', 'Computer Science', 'Semester 3'),
            ('IT201', 'Cloud Computing & DevOps', 'Information Technology', 'Semester 5'),
            ('EC301', 'Embedded Systems & IoT', 'Electronics', 'Semester 6'),
            ('ME401', 'Robotics & Automation', 'Mechanical', 'Semester 7')
        ]
        cursor.executemany("INSERT INTO subjects (code, name, department, semester) VALUES (?, ?, ?, ?)", subjects_data)

    # Seed sample students if table is empty
    cursor.execute("SELECT COUNT(*) as count FROM students")
    if cursor.fetchone()['count'] == 0:
        sample_students = [
            ('CS202601', 'Ethan Davis', 'ethan.davis@college.edu', 'Computer Science', '3rd Year', 'Male', '+1 (555) 234-5678', 'CS202601.jpg'),
            ('CS202602', 'Sophia Rodriguez', 'sophia.r@college.edu', 'Computer Science', '3rd Year', 'Female', '+1 (555) 345-6789', 'CS202602.jpg'),
            ('IT202603', 'Aiden Clark', 'aiden.clark@college.edu', 'Information Technology', '2nd Year', 'Male', '+1 (555) 456-7890', 'IT202603.jpg'),
            ('EC202604', 'Emma Watson', 'emma.watson@college.edu', 'Electronics', '4th Year', 'Female', '+1 (555) 567-8901', 'EC202604.jpg'),
            ('ME202605', 'Lucas Miller', 'lucas.m@college.edu', 'Mechanical', '1st Year', 'Male', '+1 (555) 678-9012', 'ME202605.jpg')
        ]
        
        default_student_pw = generate_password_hash('student123')
        today = date.today()
        
        for roll, name, email, dept, yr, gender, phone, photo in sample_students:
            cursor.execute("""
            INSERT INTO students (roll_number, name, email, department, year, gender, phone, photo_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (roll, name, email, dept, yr, gender, phone, photo))
            
            student_id = cursor.lastrowid
            cursor.execute("""
            INSERT INTO student_credentials (student_id, roll_number, password_hash)
            VALUES (?, ?, ?)
            """, (student_id, roll, default_student_pw))
            
            # Generate 14 days of realistic past attendance
            for days_ago in range(14, 0, -1):
                past_date = today - timedelta(days=days_ago)
                # Skip Sundays
                if past_date.weekday() == 6:
                    continue
                
                # Deterministic pattern based on student id and day
                status = 'Present'
                if (student_id + past_date.day) % 7 == 0:
                    status = 'Absent'
                elif (student_id + past_date.day) % 5 == 0:
                    status = 'Late'
                
                mode = 'Face Recognition' if status != 'Absent' else 'Manual'
                conf = 94.5 if status == 'Present' else (88.0 if status == 'Late' else 0.0)
                record_time = "09:05:14" if status == 'Present' else ("09:28:40" if status == 'Late' else "00:00:00")
                
                cursor.execute("""
                INSERT OR IGNORE INTO attendance (student_id, roll_number, date, time, status, verification_mode, confidence_score, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (student_id, roll, past_date.isoformat(), record_time, status, mode, conf, 'Regular class attendance'))

    conn.commit()
    conn.close()

# ----------------- ADMIN OPERATIONS -----------------

def get_admin_by_username(username):
    conn = get_db_connection()
    admin = conn.execute("SELECT * FROM admins WHERE username = ? OR email = ?", (username, username)).fetchone()
    conn.close()
    return admin

def get_admin_by_id(admin_id):
    conn = get_db_connection()
    admin = conn.execute("SELECT * FROM admins WHERE id = ?", (admin_id,)).fetchone()
    conn.close()
    return admin

def update_admin_profile(admin_id, full_name, email, password=None):
    conn = get_db_connection()
    if password:
        hashed_pw = generate_password_hash(password)
        conn.execute("""
        UPDATE admins SET full_name = ?, email = ?, password_hash = ? WHERE id = ?
        """, (full_name, email, hashed_pw, admin_id))
    else:
        conn.execute("""
        UPDATE admins SET full_name = ?, email = ? WHERE id = ?
        """, (full_name, email, admin_id))
    conn.commit()
    conn.close()

# ----------------- STUDENT OPERATIONS -----------------

def add_student(roll_number, name, email, department, year, gender='Other', phone='', photo_path='', initial_password='student123'):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO students (roll_number, name, email, department, year, gender, phone, photo_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (roll_number.strip().upper(), name.strip(), email.strip().lower(), department, year, gender, phone, photo_path))
        
        student_id = cursor.lastrowid
        pw_hash = generate_password_hash(initial_password)
        cursor.execute("""
        INSERT INTO student_credentials (student_id, roll_number, password_hash)
        VALUES (?, ?, ?)
        """, (student_id, roll_number.strip().upper(), pw_hash))
        
        conn.commit()
        return student_id, None
    except sqlite3.IntegrityError as e:
        conn.rollback()
        return None, "A student with this Roll Number already exists."
    except Exception as e:
        conn.rollback()
        return None, str(e)
    finally:
        conn.close()

def get_all_students(search=None, department=None, year=None):
    conn = get_db_connection()
    query = "SELECT * FROM students WHERE is_active = 1"
    params = []

    if search:
        search_param = f"%{search.strip()}%"
        query += " AND (name LIKE ? OR roll_number LIKE ? OR email LIKE ?)"
        params.extend([search_param, search_param, search_param])

    if department:
        query += " AND department = ?"
        params.append(department)

    if year:
        query += " AND year = ?"
        params.append(year)

    query += " ORDER BY roll_number ASC"
    students = conn.execute(query, params).fetchall()
    conn.close()
    return students

def get_student_by_id(student_id):
    conn = get_db_connection()
    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    conn.close()
    return student

def get_student_by_roll(roll_number):
    conn = get_db_connection()
    student = conn.execute("SELECT * FROM students WHERE roll_number = ? COLLATE NOCASE", (roll_number.strip(),)).fetchone()
    conn.close()
    return student

def update_student(student_id, name, email, department, year, gender, phone, photo_path=None):
    conn = get_db_connection()
    try:
        if photo_path:
            conn.execute("""
            UPDATE students
            SET name = ?, email = ?, department = ?, year = ?, gender = ?, phone = ?, photo_path = ?
            WHERE id = ?
            """, (name.strip(), email.strip().lower(), department, year, gender, phone, photo_path, student_id))
        else:
            conn.execute("""
            UPDATE students
            SET name = ?, email = ?, department = ?, year = ?, gender = ?, phone = ?
            WHERE id = ?
            """, (name.strip(), email.strip().lower(), department, year, gender, phone, student_id))
        conn.commit()
        return True, None
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

def delete_student(student_id):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
        conn.commit()
        return True, None
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

# ----------------- STUDENT AUTH -----------------

def get_student_credential(roll_number):
    conn = get_db_connection()
    credential = conn.execute("""
    SELECT sc.*, s.name, s.email, s.department, s.year, s.photo_path
    FROM student_credentials sc
    JOIN students s ON sc.student_id = s.id
    WHERE sc.roll_number = ? COLLATE NOCASE AND s.is_active = 1
    """, (roll_number.strip(),)).fetchone()
    conn.close()
    return credential

def update_student_password(student_id, new_password):
    conn = get_db_connection()
    hashed = generate_password_hash(new_password)
    conn.execute("UPDATE student_credentials SET password_hash = ? WHERE student_id = ?", (hashed, student_id))
    conn.commit()
    conn.close()

# ----------------- FACE ENCODING RECORDS -----------------

def save_face_encoding(student_id, roll_number, image_path, encoding_blob=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO face_encodings (student_id, roll_number, image_path, encoding_blob)
    VALUES (?, ?, ?, ?)
    """, (student_id, roll_number, image_path, encoding_blob))
    
    # Also update students table photo_path if not set
    cursor.execute("UPDATE students SET photo_path = ? WHERE id = ?", (image_path, student_id))
    conn.commit()
    conn.close()

def get_all_registered_faces():
    conn = get_db_connection()
    faces = conn.execute("""
    SELECT fe.*, s.name, s.department
    FROM face_encodings fe
    JOIN students s ON fe.student_id = s.id
    WHERE s.is_active = 1
    """).fetchall()
    conn.close()
    return faces

# ----------------- ATTENDANCE OPERATIONS -----------------

def mark_attendance(student_id, roll_number, status='Present', verification_mode='Face Recognition', confidence_score=95.0, notes='', att_date=None, att_time=None):
    """
    Marks attendance for a student on a given date.
    Returns: (success: bool, message: str, attendance_record: dict)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    today_str = att_date if att_date else date.today().isoformat()
    now_time = att_time if att_time else datetime.now().strftime("%H:%M:%S")

    # Check if already marked for today
    cursor.execute("SELECT * FROM attendance WHERE student_id = ? AND date = ?", (student_id, today_str))
    existing = cursor.fetchone()

    if existing:
        conn.close()
        return False, f"Attendance already marked for today ({existing['status']}) at {existing['time']}.", dict(existing)

    try:
        cursor.execute("""
        INSERT INTO attendance (student_id, roll_number, date, time, status, verification_mode, confidence_score, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (student_id, roll_number, today_str, now_time, status, verification_mode, confidence_score, notes))
        
        att_id = cursor.lastrowid
        conn.commit()
        
        cursor.execute("""
        SELECT a.*, s.name, s.department, s.photo_path
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE a.id = ?
        """, (att_id,))
        record = cursor.fetchone()
        conn.close()
        return True, f"Attendance marked successfully as {status}!", dict(record) if record else None
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, f"Error saving attendance: {str(e)}", None

def update_attendance_status(attendance_id, status, notes=""):
    conn = get_db_connection()
    conn.execute("UPDATE attendance SET status = ?, notes = ? WHERE id = ?", (status, notes, attendance_id))
    conn.commit()
    conn.close()

def delete_attendance_record(attendance_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM attendance WHERE id = ?", (attendance_id,))
    conn.commit()
    conn.close()

def get_today_attendance():
    today_str = date.today().isoformat()
    conn = get_db_connection()
    records = conn.execute("""
    SELECT a.*, s.name, s.department, s.year, s.photo_path
    FROM attendance a
    JOIN students s ON a.student_id = s.id
    WHERE a.date = ?
    ORDER BY a.time DESC
    """, (today_str,)).fetchall()
    conn.close()
    return records

def get_filtered_attendance(date_filter=None, department=None, year=None, status=None, search=None):
    conn = get_db_connection()
    query = """
    SELECT a.*, s.name, s.department, s.year, s.photo_path, s.email
    FROM attendance a
    JOIN students s ON a.student_id = s.id
    WHERE 1=1
    """
    params = []

    if date_filter:
        query += " AND a.date = ?"
        params.append(date_filter)

    if department:
        query += " AND s.department = ?"
        params.append(department)

    if year:
        query += " AND s.year = ?"
        params.append(year)

    if status:
        query += " AND a.status = ?"
        params.append(status)

    if search:
        search_term = f"%{search.strip()}%"
        query += " AND (s.name LIKE ? OR a.roll_number LIKE ?)"
        params.extend([search_term, search_term])

    query += " ORDER BY a.date DESC, a.time DESC"
    records = conn.execute(query, params).fetchall()
    conn.close()
    return records

def get_student_attendance_history(student_id):
    conn = get_db_connection()
    records = conn.execute("""
    SELECT a.*, s.name, s.department
    FROM attendance a
    JOIN students s ON a.student_id = s.id
    WHERE a.student_id = ?
    ORDER BY a.date DESC
    """, (student_id,)).fetchall()
    conn.close()
    return records

# ----------------- ANALYTICS & DASHBOARD METRICS -----------------

def get_dashboard_metrics():
    """Calculates all key dynamic dashboard statistics from database."""
    conn = get_db_connection()
    today_str = date.today().isoformat()

    # Total registered active students
    total_students = conn.execute("SELECT COUNT(*) FROM students WHERE is_active = 1").fetchone()[0]

    # Today's attendance counts
    present_today = conn.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'Present'", (today_str,)).fetchone()[0]
    late_today = conn.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'Late'", (today_str,)).fetchone()[0]
    absent_today = conn.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'Absent'", (today_str,)).fetchone()[0]
    
    total_marked_today = present_today + late_today + absent_today
    effective_present = present_today + late_today
    
    # If some students are not marked yet today, treat them as pending/unmarked
    unmarked_today = max(0, total_students - total_marked_today)
    
    today_percentage = round((effective_present / total_students * 100), 1) if total_students > 0 else 0.0

    # Overall attendance percentage across all records
    overall_total = conn.execute("SELECT COUNT(*) FROM attendance").fetchone()[0]
    overall_present = conn.execute("SELECT COUNT(*) FROM attendance WHERE status IN ('Present', 'Late')").fetchone()[0]
    overall_percentage = round((overall_present / overall_total * 100), 1) if overall_total > 0 else 0.0

    conn.close()
    return {
        'total_students': total_students,
        'present_today': present_today,
        'late_today': late_today,
        'absent_today': absent_today,
        'unmarked_today': unmarked_today,
        'today_percentage': today_percentage,
        'overall_percentage': overall_percentage
    }

def get_weekly_chart_data():
    """Returns past 7 days attendance trends for Chart.js."""
    conn = get_db_connection()
    today = date.today()
    labels = []
    present_counts = []
    absent_counts = []
    late_counts = []

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_str = day.isoformat()
        labels.append(day.strftime("%a (%d %b)"))

        p = conn.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'Present'", (day_str,)).fetchone()[0]
        l = conn.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'Late'", (day_str,)).fetchone()[0]
        a = conn.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'Absent'", (day_str,)).fetchone()[0]

        present_counts.append(p)
        late_counts.append(l)
        absent_counts.append(a)

    conn.close()
    return {
        'labels': labels,
        'present': present_counts,
        'late': late_counts,
        'absent': absent_counts
    }

def get_department_stats():
    """Returns department-wise distribution and attendance counts."""
    conn = get_db_connection()
    today_str = date.today().isoformat()

    departments = conn.execute("""
    SELECT department, COUNT(*) as student_count
    FROM students
    WHERE is_active = 1
    GROUP BY department
    """).fetchall()

    dept_names = []
    student_totals = []
    present_totals = []

    for d in departments:
        dept = d['department']
        dept_names.append(dept)
        student_totals.append(d['student_count'])

        # Present today in this department
        p = conn.execute("""
        SELECT COUNT(a.id)
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE s.department = ? AND a.date = ? AND a.status IN ('Present', 'Late')
        """, (dept, today_str)).fetchone()[0]
        present_totals.append(p)

    conn.close()
    return {
        'departments': dept_names,
        'total_students': student_totals,
        'present_students': present_totals
    }

def get_student_personal_stats(student_id):
    """Calculates single student statistics for student portal."""
    conn = get_db_connection()
    total_days = conn.execute("SELECT COUNT(*) FROM attendance WHERE student_id = ?", (student_id,)).fetchone()[0]
    present_days = conn.execute("SELECT COUNT(*) FROM attendance WHERE student_id = ? AND status = 'Present'", (student_id,)).fetchone()[0]
    late_days = conn.execute("SELECT COUNT(*) FROM attendance WHERE student_id = ? AND status = 'Late'", (student_id,)).fetchone()[0]
    absent_days = conn.execute("SELECT COUNT(*) FROM attendance WHERE student_id = ? AND status = 'Absent'", (student_id,)).fetchone()[0]

    effective_present = present_days + late_days
    pct = round((effective_present / total_days * 100), 1) if total_days > 0 else 0.0

    conn.close()
    return {
        'total_classes': total_days,
        'present': present_days,
        'late': late_days,
        'absent': absent_days,
        'percentage': pct,
        'is_low_attendance': pct < 75.0 and total_days > 0
    }

def get_low_attendance_students(threshold=75.0):
    """Returns list of students whose attendance is below the threshold percentage."""
    conn = get_db_connection()
    students = conn.execute("SELECT * FROM students WHERE is_active = 1").fetchall()
    low_att_list = []

    for s in students:
        total = conn.execute("SELECT COUNT(*) FROM attendance WHERE student_id = ?", (s['id'],)).fetchone()[0]
        if total > 0:
            present = conn.execute("SELECT COUNT(*) FROM attendance WHERE student_id = ? AND status IN ('Present', 'Late')", (s['id'],)).fetchone()[0]
            pct = round((present / total * 100), 1)
            if pct < threshold:
                student_dict = dict(s)
                student_dict['attendance_percentage'] = pct
                student_dict['total_days'] = total
                student_dict['absent_days'] = total - present
                low_att_list.append(student_dict)

    conn.close()
    return low_att_list
