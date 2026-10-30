# AttendifyAI — Student Online Attendance Detection System using Python & AI Face Recognition

[![Python Version](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://python.org)
[![Framework](https://img.shields.io/badge/Backend-Flask%203.1-emerald.svg)](https://flask.palletsprojects.com/)
[![Computer Vision](https://img.shields.io/badge/AI%20Vision-OpenCV%20LBPH%20%2B%20Haar-orange.svg)](https://opencv.org/)
[![UI Design](https://img.shields.io/badge/Design-Enterprise%20Navy%20%26%20Light%20Blue-0f172a.svg)](https://getbootstrap.com/)

**AttendifyAI** is a commercial-grade, end-to-end **Student Online Attendance Detection System** powered by Python Flask, OpenCV computer vision, and LBPH facial recognition biometrics. Designed to look and function like a real commercial SaaS enterprise application.

---

## 🌟 Key Features

### 1. 🛡️ Role-Based Authentication & Portals
- **Administrator Portal:** Full system oversight, biometric enrollment, live camera monitoring, student records management, manual attendance overrides, and institutional reporting.
- **Student Portal:** Personalized attendance dashboard with self-attendance percentage dials, present/late/absent counters, complete attendance logs, and report exports.
- **Security:** Password hashing (`PBKDF2-HMAC-SHA256` via Werkzeug), session authentication guards (`@admin_required`, `@student_required`), role separation, and student data isolation.

### 2. 🤖 Live AI Camera Face Detection & Recognition
- **Real-Time Detection:** Connects to the web camera via HTML5 `getUserMedia` or server-side OpenCV `cv2.VideoCapture`.
- **Facial Recognition Engine:** Utilizes OpenCV Haar Cascade Classifiers for face detection and Local Binary Patterns Histograms (LBPH) for illumination-invariant recognition.
- **Real-Time HUD Overlay:** Draws green bounding boxes for recognized students (showing Student Name, Roll Number, and Confidence %) and red bounding boxes with **"Unknown Person"** alerts for unregistered faces.
- **Automatic Attendance Marking:** Automatically marks attendance as **Present** when a registered student is detected.
- **Anti-Duplicate Protocol:** Strictly prevents multiple attendance records for the same student on the same day; displays an informational "Already Recorded for Today at HH:MM:SS" banner and skips duplicate database writes.
- **Audio Chime:** Plays an audio chime upon successful biometric verification.

### 3. 🎓 Student Management & Biometric Enrollment
- Full CRUD: Register, view, edit, search, filter, and delete students.
- **Multi-Shot Webcam Biometric Tool:** Rapidly captures 5 face angles directly from the browser webcam with automated data augmentation (illumination adjustments & horizontal mirroring).
- **Photo Upload Support:** Alternative file upload mode for frontal portrait photos.
- **Automatic Retraining:** Model automatically re-trains in background immediately upon enrollment or deletion.

### 4. 📊 Attendance Registry & Manual Overrides
- Complete date-wise, department-wise, and status-wise attendance records.
- Instructor/Admin **Manual Attendance Override Modal** (mark Present, Late, or Absent with notes).
- Status update and record deletion capabilities.

### 5. 📈 Reports, Analytics & Exports
- Dynamic dashboard statistics fetched in real-time from the database.
- Interactive Chart.js visualizations (Weekly Attendance Trends & Department Distribution).
- **Low Attendance Defaulter Alerts:** Automatically identifies students with attendance below 75%.
- **One-Click Exports:**
  - **Excel (.xlsx):** Professionally styled with navy headers, status color pills, auto-column widths, and gridlines.
  - **CSV (.csv):** UTF-8 encoded with BOM for full spreadsheet compatibility.

---

## 🏗️ Project Architecture

```
project/
│
├── app.py                         # Main Flask application and REST routes
├── database.py                    # SQLite database schema, connections, and CRUD
├── face_recognition_module.py     # OpenCV Haar Cascade & LBPH Face Recognition engine
├── attendance.py                  # Attendance business logic, CSV & Excel exports
├── haarcascade_frontalface_default.xml # Pre-trained OpenCV Haar Cascade face detector
├── test_system.py                 # Automated unit and integration test suite
├── requirements.txt               # Python package dependencies
├── attendance.db                  # Persistent SQLite database file
│
├── templates/                     # Jinja2 HTML5 UI templates
│   ├── base.html                  # Global layout with enterprise responsive sidebar
│   ├── auth/
│   │   ├── login.html             # Tabbed login for Admins & Students
│   │   └── register.html          # Student self-registration form
│   ├── admin/
│   │   ├── dashboard.html         # Executive metrics cards & Chart.js graphs
│   │   ├── students.html          # Student records directory with search & filters
│   │   ├── student_add.html       # Student enrollment & multi-shot webcam tool
│   │   ├── student_edit.html      # Student details and photo editor
│   │   ├── student_profile.html   # Detailed student profile & attendance log
│   │   ├── live_camera.html       # AI Live Camera Face Detection Console
│   │   ├── attendance.html        # Attendance management & manual override modal
│   │   └── reports.html           # Institutional reports & low attendance alerts
│   └── student/
│       ├── dashboard.html         # Student personal attendance dashboard
│       ├── my_attendance.html     # Student personal attendance history
│       └── profile.html           # Student profile & password settings
│
├── static/
│   ├── css/
│   │   └── style.css              # Custom Enterprise Navy/Light Blue design system
│   └── js/
│       ├── main.js                # UI utilities, real-time clock, Chart.js loaders
│       └── camera.js              # Webcam streaming, canvas HUD, recognition loop
│
└── uploads/
    ├── faces/                     # Stored face samples organized by student ID
    └── trained/
        └── face_trainer.yml       # Trained LBPH biometric model weights
```

---

## ⚡ Quick Start & Installation

### 1. Prerequisites
- Python 3.10, 3.11, 3.12, or 3.13 installed.
- A functional web camera (integrated laptop webcam or USB camera).

### 2. Install Required Dependencies
In your terminal / PowerShell, run:
```bash
python -m pip install -r requirements.txt
```

### 3. Launch the Application Server
Run:
```bash
python app.py
```

The application will start on:
👉 **`http://127.0.0.1:5000`** (or `http://localhost:5000`)

---

## 🔑 Default Credentials

The database comes pre-seeded with sample records and default logins:

### 🛡️ System Administrator
- **URL:** `http://127.0.0.1:5000/login` (Select "Administrator" tab)
- **Username:** `admin`
- **Password:** `admin123`

### 🎓 Sample Students
- **URL:** `http://127.0.0.1:5000/login` (Select "Student Portal" tab)
- **Student 1 (Ethan Davis):** Roll Number: `CS202601` | Password: `student123`
- **Student 2 (Sophia Rodriguez):** Roll Number: `CS202602` | Password: `student123`
- **Student 3 (Aiden Clark):** Roll Number: `IT202603` | Password: `student123`
- **Student 4 (Emma Watson):** Roll Number: `EC202604` | Password: `student123`
- **Student 5 (Lucas Miller):** Roll Number: `ME202605` | Password: `student123`

---

## 🧪 Running Automated Tests

Run the built-in test suite to verify all modules and security gates:
```bash
python test_system.py
```

Output:
```
Ran 6 tests in 6.5s
OK
```

---

## 📋 Technology Stack Summary

| Layer | Technologies Used |
|---|---|
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3, FontAwesome 6, Chart.js, SweetAlert2 |
| **Backend** | Python 3, Flask 3.1, Werkzeug |
| **Database** | SQLite3 (Persistent file `attendance.db` with relational schema) |
| **AI / Vision** | OpenCV 5 (`opencv-contrib-python`), LBPH Face Recognizer, Haar Cascade Classifier |
| **Export Engines** | `openpyxl` (Native Excel .xlsx with styling), `csv` (RFC 4180 with UTF-8 BOM) |
