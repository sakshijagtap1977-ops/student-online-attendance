"""
app.py - Main Flask Application Server
Student Online Attendance Detection System using Python and AI-based Face Recognition.
"""

import os
import cv2
import numpy as np
import base64
from functools import wraps
from datetime import datetime, date, timedelta

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, send_file, Response, make_response
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

import database
import attendance
import face_recognition_module

# Initialize Application
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'attendify-secure-enterprise-jwt-key-9923847')
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload

# Ensure database tables and initial sample data are seeded
database.init_db()

# -------------------------------------------------------------
# AUTHENTICATION DECORATORS
# -------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this portal.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Access restricted to System Administrators.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'student':
            flash('Access restricted to enrolled Students.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Context processor for templates
@app.context_processor
def inject_global_data():
    return {
        'current_year': datetime.now().year,
        'today_date': date.today().strftime('%A, %d %B %Y'),
        'session_user': session
    }

# -------------------------------------------------------------
# LANDING & AUTHENTICATION ROUTES
# -------------------------------------------------------------

@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif session.get('role') == 'student':
            return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_type = request.form.get('user_type', 'admin') # 'admin' or 'student'
        username_or_roll = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username_or_roll or not password:
            flash('Please enter both identifier and password.', 'warning')
            return render_template('auth/login.html')

        if user_type == 'admin':
            admin = database.get_admin_by_username(username_or_roll)
            if admin and check_password_hash(admin['password_hash'], password):
                session.clear()
                session['user_id'] = admin['id']
                session['username'] = admin['username']
                session['name'] = admin['full_name']
                session['email'] = admin['email']
                session['role'] = 'admin'
                flash(f"Welcome back, {admin['full_name']}!", 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid Administrator username or password.', 'danger')

        elif user_type == 'student':
            cred = database.get_student_credential(username_or_roll)
            if cred and check_password_hash(cred['password_hash'], password):
                session.clear()
                session['user_id'] = cred['student_id']
                session['roll_number'] = cred['roll_number']
                session['name'] = cred['name']
                session['email'] = cred['email']
                session['department'] = cred['department']
                session['photo_path'] = cred['photo_path']
                session['role'] = 'student'
                flash(f"Welcome, {cred['name']}!", 'success')
                return redirect(url_for('student_dashboard'))
            else:
                flash('Invalid Roll Number or Student password.', 'danger')

    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out securely.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def student_self_register():
    """Allows student self-registration."""
    if request.method == 'POST':
        roll = request.form.get('roll_number', '').strip().upper()
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        dept = request.form.get('department', '')
        year = request.form.get('year', '')
        gender = request.form.get('gender', 'Other')
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')

        if not roll or not name or not email or not password:
            flash('Please fill in all required fields.', 'warning')
            return render_template('auth/register.html')

        student_id, err = database.add_student(
            roll_number=roll,
            name=name,
            email=email,
            department=dept,
            year=year,
            gender=gender,
            phone=phone,
            initial_password=password
        )

        if err:
            flash(err, 'danger')
            return render_template('auth/register.html')

        flash('Registration successful! You may now log in with your Roll Number and password.', 'success')
        return redirect(url_for('login'))

    return render_template('auth/register.html')

# -------------------------------------------------------------
# ADMIN DASHBOARD & MANAGEMENT ROUTES
# -------------------------------------------------------------

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    stats = database.get_dashboard_metrics()
    today_records = database.get_today_attendance()
    low_attendance = database.get_low_attendance_students(threshold=75.0)
    
    return render_template(
        'admin/dashboard.html',
        stats=stats,
        recent_records=today_records[:10],
        low_attendance=low_attendance[:5]
    )

@app.route('/admin/students')
@admin_required
def admin_students():
    search = request.args.get('search', '')
    department = request.args.get('department', '')
    year = request.args.get('year', '')

    students = database.get_all_students(
        search=search if search else None,
        department=department if department and department != 'All' else None,
        year=year if year and year != 'All' else None
    )

    return render_template(
        'admin/students.html',
        students=students,
        search=search,
        selected_dept=department,
        selected_year=year
    )

@app.route('/admin/students/add', methods=['GET', 'POST'])
@admin_required
def admin_student_add():
    if request.method == 'POST':
        roll = request.form.get('roll_number', '').strip().upper()
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        dept = request.form.get('department', 'Computer Science')
        year = request.form.get('year', '1st Year')
        gender = request.form.get('gender', 'Male')
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', 'student123')

        if not roll or not name or not email:
            flash('Name, Roll Number, and Email are mandatory.', 'warning')
            return render_template('admin/student_add.html')

        # 1. Create student in database
        student_id, err = database.add_student(
            roll_number=roll,
            name=name,
            email=email,
            department=dept,
            year=year,
            gender=gender,
            phone=phone,
            initial_password=password
        )

        if err:
            flash(err, 'danger')
            return render_template('admin/student_add.html')

        # 2. Process face images: check for webcam snapshots or uploaded file
        face_sources = []

        # From live camera multi-shots
        webcam_snapshots = request.form.getlist('webcam_snapshots[]')
        for snap in webcam_snapshots:
            if snap and snap.startswith('data:image'):
                face_sources.append(snap)

        # From file upload
        uploaded_file = request.files.get('face_image_file')
        if uploaded_file and uploaded_file.filename != '':
            ext = secure_filename(uploaded_file.filename).rsplit('.', 1)[-1].lower()
            if ext in ['jpg', 'jpeg', 'png', 'webp']:
                temp_filename = f"temp_{student_id}_{int(datetime.now().timestamp())}.{ext}"
                temp_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
                uploaded_file.save(temp_path)
                face_sources.append(temp_path)

        # Register face biometric models
        if face_sources:
            reg_ok, count, reg_msg = face_recognition_module.engine.register_student_faces(
                student_id=student_id,
                roll_number=roll,
                image_sources=face_sources
            )
            flash(f"Student {name} registered! {reg_msg}", 'success' if reg_ok else 'warning')
        else:
            flash(f"Student {name} registered! Please capture/upload face photos to enable facial recognition.", 'info')

        return redirect(url_for('admin_students'))

    return render_template('admin/student_add.html')

@app.route('/admin/students/edit/<int:student_id>', methods=['GET', 'POST'])
@admin_required
def admin_student_edit(student_id):
    student = database.get_student_by_id(student_id)
    if not student:
        flash('Student record not found.', 'danger')
        return redirect(url_for('admin_students'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        dept = request.form.get('department', '')
        year = request.form.get('year', '')
        gender = request.form.get('gender', '')
        phone = request.form.get('phone', '').strip()

        # Check for new face images
        face_sources = []
        webcam_snapshots = request.form.getlist('webcam_snapshots[]')
        for snap in webcam_snapshots:
            if snap and snap.startswith('data:image'):
                face_sources.append(snap)

        uploaded_file = request.files.get('face_image_file')
        if uploaded_file and uploaded_file.filename != '':
            ext = secure_filename(uploaded_file.filename).rsplit('.', 1)[-1].lower()
            if ext in ['jpg', 'jpeg', 'png', 'webp']:
                temp_filename = f"temp_{student_id}_{int(datetime.now().timestamp())}.{ext}"
                temp_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
                uploaded_file.save(temp_path)
                face_sources.append(temp_path)

        if face_sources:
            face_recognition_module.engine.register_student_faces(
                student_id=student_id,
                roll_number=student['roll_number'],
                image_sources=face_sources
            )

        ok, err = database.update_student(student_id, name, email, dept, year, gender, phone)
        if ok:
            flash('Student details updated successfully.', 'success')
            return redirect(url_for('admin_student_profile', student_id=student_id))
        else:
            flash(f"Error updating details: {err}", 'danger')

    return render_template('admin/student_edit.html', student=student)

@app.route('/admin/students/profile/<int:student_id>')
@admin_required
def admin_student_profile(student_id):
    student = database.get_student_by_id(student_id)
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('admin_students'))

    stats = database.get_student_personal_stats(student_id)
    history = database.get_student_attendance_history(student_id)
    
    return render_template(
        'admin/student_profile.html',
        student=student,
        stats=stats,
        history=history
    )

@app.route('/admin/students/delete/<int:student_id>', methods=['POST'])
@admin_required
def admin_student_delete(student_id):
    student = database.get_student_by_id(student_id)
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('admin_students'))

    # Clean up student faces folder if present
    folder = os.path.join(app.config['UPLOAD_FOLDER'], 'faces', f"{student_id}_{student['roll_number']}")
    if os.path.exists(folder):
        try:
            import shutil
            shutil.rmtree(folder)
        except Exception:
            pass

    ok, err = database.delete_student(student_id)
    if ok:
        # Re-train model to omit deleted student
        face_recognition_module.engine.train_model()
        flash(f"Student {student['name']} deleted successfully.", 'success')
    else:
        flash(f"Error deleting student: {err}", 'danger')

    return redirect(url_for('admin_students'))

# -------------------------------------------------------------
# LIVE CAMERA ATTENDANCE MODULE
# -------------------------------------------------------------

@app.route('/admin/camera')
@admin_required
def live_camera():
    today_records = database.get_today_attendance()
    stats = database.get_dashboard_metrics()
    return render_template(
        'admin/live_camera.html',
        recent_records=today_records,
        stats=stats,
        is_model_trained=face_recognition_module.engine.is_trained
    )

@app.route('/api/recognize_frame', methods=['POST'])
@admin_required
def api_recognize_frame():
    """
    Receives base64 webcam frame from browser JS,
    runs face detection & LBPH recognition, marks attendance,
    and returns bounding box coordinates and recognized student info.
    """
    data = request.get_json(silent=True) or {}
    image_b64 = data.get('image', '')
    auto_mark = data.get('auto_mark', True)

    if not image_b64:
        return jsonify({'success': False, 'error': 'No image provided'}), 400

    try:
        if ',' in image_b64:
            image_b64 = image_b64.split(',', 1)[1]
        
        img_bytes = base64.b64decode(image_b64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({'success': False, 'error': 'Failed to decode image frame'}), 400

        results, _ = face_recognition_module.engine.process_frame(frame, auto_mark=auto_mark)

        return jsonify({
            'success': True,
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'faces_detected': len(results),
            'results': results
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/camera_control', methods=['POST'])
@admin_required
def api_camera_control():
    data = request.get_json(silent=True) or {}
    action = data.get('action', '')

    if action == 'start':
        started = face_recognition_module.camera_controller.start_camera()
        return jsonify({'success': started, 'status': 'running' if started else 'failed'})
    elif action == 'stop':
        face_recognition_module.camera_controller.stop_camera()
        return jsonify({'success': True, 'status': 'stopped'})
    else:
        return jsonify({'success': False, 'error': 'Invalid action'}), 400

def generate_video_stream():
    """MJPEG streaming generator using OpenCV backend capture."""
    while face_recognition_module.camera_controller.is_running:
        frame = face_recognition_module.camera_controller.get_frame()
        if frame is None:
            continue

        # Process frame with face recognizer
        results, annotated = face_recognition_module.engine.process_frame(frame, auto_mark=True)

        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ret:
            continue

        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed')
@admin_required
def video_feed():
    """Direct OpenCV VideoCapture MJPEG stream route."""
    if not face_recognition_module.camera_controller.is_running:
        face_recognition_module.camera_controller.start_camera()

    return Response(
        generate_video_stream(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

# -------------------------------------------------------------
# ATTENDANCE MANAGEMENT & MANUAL MARKING
# -------------------------------------------------------------

@app.route('/admin/attendance')
@admin_required
def admin_attendance():
    date_filter = request.args.get('date', date.today().isoformat())
    dept_filter = request.args.get('department', '')
    year_filter = request.args.get('year', '')
    status_filter = request.args.get('status', '')
    search = request.args.get('search', '')

    records = database.get_filtered_attendance(
        date_filter=date_filter if date_filter and date_filter != 'all' else None,
        department=dept_filter if dept_filter and dept_filter != 'All' else None,
        year=year_filter if year_filter and year_filter != 'All' else None,
        status=status_filter if status_filter and status_filter != 'All' else None,
        search=search if search else None
    )

    all_students = database.get_all_students()

    return render_template(
        'admin/attendance.html',
        records=records,
        students=all_students,
        current_date=date_filter,
        dept_filter=dept_filter,
        year_filter=year_filter,
        status_filter=status_filter,
        search=search
    )

@app.route('/admin/attendance/manual', methods=['POST'])
@admin_required
def admin_manual_attendance():
    student_id = request.form.get('student_id')
    status = request.form.get('status', 'Present')
    att_date = request.form.get('attendance_date', date.today().isoformat())
    notes = request.form.get('notes', 'Admin manual verification')

    student = database.get_student_by_id(student_id)
    if not student:
        flash('Student record not found.', 'danger')
        return redirect(url_for('admin_attendance'))

    ok, msg, rec = database.mark_attendance(
        student_id=student['id'],
        roll_number=student['roll_number'],
        status=status,
        verification_mode='Manual',
        confidence_score=100.0,
        notes=notes,
        att_date=att_date
    )

    if ok:
        flash(msg, 'success')
    else:
        flash(msg, 'warning')

    return redirect(url_for('admin_attendance', date=att_date))

@app.route('/admin/attendance/update/<int:attendance_id>', methods=['POST'])
@admin_required
def admin_update_attendance(attendance_id):
    status = request.form.get('status')
    notes = request.form.get('notes', '')
    database.update_attendance_status(attendance_id, status, notes)
    flash('Attendance record updated successfully.', 'success')
    return redirect(request.referrer or url_for('admin_attendance'))

@app.route('/admin/attendance/delete/<int:attendance_id>', methods=['POST'])
@admin_required
def admin_delete_attendance(attendance_id):
    database.delete_attendance_record(attendance_id)
    flash('Attendance record deleted.', 'info')
    return redirect(request.referrer or url_for('admin_attendance'))

# -------------------------------------------------------------
# REPORTS & ANALYTICS
# -------------------------------------------------------------

@app.route('/admin/reports')
@admin_required
def admin_reports():
    report_type = request.args.get('type', 'daily')
    date_filter = request.args.get('date', date.today().isoformat())
    dept_filter = request.args.get('department', 'All')
    year_filter = request.args.get('year', 'All')

    records = attendance.get_report_data(
        report_type=report_type,
        date_filter=date_filter,
        department=dept_filter,
        year=year_filter
    )

    stats = database.get_dashboard_metrics()
    low_att_students = database.get_low_attendance_students(75.0)

    return render_template(
        'admin/reports.html',
        records=records,
        report_type=report_type,
        date_filter=date_filter,
        dept_filter=dept_filter,
        year_filter=year_filter,
        stats=stats,
        low_att_students=low_att_students
    )

@app.route('/export/attendance/<fmt>')
@login_required
def export_attendance(fmt):
    """
    Exports attendance data as CSV or Excel.
    Admins can export all filtered data; students only export their own data.
    """
    report_type = request.args.get('type', 'all')
    date_filter = request.args.get('date', None)
    dept_filter = request.args.get('department', None)
    year_filter = request.args.get('year', None)

    # Security check: if student, lock to their own ID
    student_id = None
    if session.get('role') == 'student':
        student_id = session.get('user_id')

    records = attendance.get_report_data(
        report_type=report_type,
        date_filter=date_filter,
        department=dept_filter,
        year=year_filter,
        student_id=student_id
    )

    today_str = date.today().strftime('%Y%m%d')

    if fmt == 'csv':
        csv_bytes = attendance.export_attendance_csv(records)
        response = make_response(csv_bytes)
        response.headers['Content-Disposition'] = f'attachment; filename=attendance_report_{today_str}.csv'
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        return response

    elif fmt in ['excel', 'xlsx']:
        xlsx_bytes = attendance.export_attendance_excel(records)
        response = make_response(xlsx_bytes)
        response.headers['Content-Disposition'] = f'attachment; filename=attendance_report_{today_str}.xlsx'
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        return response

    return "Invalid format", 400

# -------------------------------------------------------------
# STUDENT DASHBOARD & PERSONAL VIEWS
# -------------------------------------------------------------

@app.route('/student/dashboard')
@student_required
def student_dashboard():
    student_id = session['user_id']
    student = database.get_student_by_id(student_id)
    stats = database.get_student_personal_stats(student_id)
    history = database.get_student_attendance_history(student_id)

    # Check if marked for today
    today_str = date.today().isoformat()
    today_record = None
    for h in history:
        if h['date'] == today_str:
            today_record = h
            break

    return render_template(
        'student/dashboard.html',
        student=student,
        stats=stats,
        history=history[:8],
        today_record=today_record
    )

@app.route('/student/my-attendance')
@student_required
def student_my_attendance():
    student_id = session['user_id']
    student = database.get_student_by_id(student_id)
    stats = database.get_student_personal_stats(student_id)
    history = database.get_student_attendance_history(student_id)

    return render_template(
        'student/my_attendance.html',
        student=student,
        stats=stats,
        history=history
    )

@app.route('/student/profile', methods=['GET', 'POST'])
@student_required
def student_profile():
    student_id = session['user_id']
    student = database.get_student_by_id(student_id)

    if request.method == 'POST':
        curr_pw = request.form.get('current_password', '')
        new_pw = request.form.get('new_password', '')
        confirm_pw = request.form.get('confirm_password', '')

        cred = database.get_student_credential(student['roll_number'])
        if not check_password_hash(cred['password_hash'], curr_pw):
            flash('Current password entered is incorrect.', 'danger')
        elif len(new_pw) < 6:
            flash('New password must be at least 6 characters.', 'warning')
        elif new_pw != confirm_pw:
            flash('New password confirmation does not match.', 'danger')
        else:
            database.update_student_password(student_id, new_pw)
            flash('Your password has been updated securely!', 'success')

    return render_template('student/profile.html', student=student)

# -------------------------------------------------------------
# REST & CHART API ENDPOINTS
# -------------------------------------------------------------

@app.route('/api/dashboard_charts')
@admin_required
def api_dashboard_charts():
    weekly = database.get_weekly_chart_data()
    depts = database.get_department_stats()
    return jsonify({
        'weekly': weekly,
        'departments': depts
    })

@app.route('/api/recent_attendance')
@admin_required
def api_recent_attendance():
    records = database.get_today_attendance()
    return jsonify({
        'records': [dict(r) for r in records[:15]]
    })

# Serve uploaded files securely
@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_file(file_path)
    # Default fallback avatar if not found
    return redirect('https://ui-avatars.com/api/?name=User&background=0F172A&color=fff')

# -------------------------------------------------------------
# RUN SERVER
# -------------------------------------------------------------

if __name__ == '__main__':
    print("\n" + "="*60)
    print("  STUDENT ONLINE ATTENDANCE DETECTION SYSTEM (AI POWERED)")
    print("  Server launching at: http://127.0.0.1:5000")
    print("  Default Admin Credentials:")
    print("    Username: admin")
    print("    Password: admin123")
    print("  Default Student Credentials:")
    print("    Roll Number: CS202601")
    print("    Password:    student123")
    print("="*60 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=True)
