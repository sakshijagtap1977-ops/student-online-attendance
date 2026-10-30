# AttendifyAI — Student Online Attendance Detection System

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Flask-3.1.3-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/OpenCV-5.0%20LBPH-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white" alt="OpenCV">
  <img src="https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white" alt="Bootstrap">
  <img src="https://img.shields.io/badge/Database-SQLite3-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
</p>

> **AttendifyAI** is a commercial-grade, modern, and production-ready **Student Online Attendance Detection System** powered by Python Flask, OpenCV computer vision, and Local Binary Patterns Histograms (LBPH) facial recognition biometrics.

---

## 📌 Repository Links
- **GitHub Repository:** [https://github.com/sakshijagtap1977-ops/attendance](https://github.com/sakshijagtap1977-ops/attendance)
- **Clone URL:** `https://github.com/sakshijagtap1977-ops/attendance.git`

---

## 📸 Key Capabilities & Architecture

```
                             +------------------------+
                             |   Web Camera / Video   |
                             +-----------+------------+
                                         |
                                         v
                    +--------------------+-------------------+
                    | Client-Side WebRTC | Server-Side OpenCV |
                    | (getUserMedia API) | (VideoCapture)     |
                    +--------------------+-------------------+
                                         |
                                         v
                             +------------------------+
                             |  OpenCV Face Detection |
                             |  (Haar Cascade Model)  |
                             +-----------+------------+
                                         |
                                         v
                             +------------------------+
                             |  LBPH Face Recognizer  |
                             |  (Biometric Inference) |
                             +-----------+------------+
                                         |
                   +---------------------+---------------------+
                   |                                           |
                   v (Recognized >= 70%)                       v (Unknown Face)
      +----------------------------+             +---------------------------+
      |  Auto Mark Attendance      |             |  "Unknown Person" Alert   |
      |  Anti-Duplicate Check      |             |  Red HUD Bounding Box     |
      |  Audio Chime & Toast       |             +---------------------------+
      +--------------+-------------+
                     |
                     v
      +----------------------------+
      |  SQLite Persistent DB      |
      |  Attendance & Biometrics   |
      +----------------------------+
```

---

## 🌟 Features Breakdown

### 1. 🛡️ Role-Based Authentication & Portals
- **Administrator Console:**
  - Executive dashboard with real-time biometric metrics.
  - Live AI camera feed with HUD overlays.
  - Full student CRUD directory with search and multi-criteria filters.
  - Manual attendance override modal (Present, Late, Absent).
  - Daily, weekly, and monthly institutional reports.
  - Low attendance (< 75%) defaulter warning triggers.
- **Student Self-Service Portal:**
  - Dedicated student login using **Roll Number** & Password.
  - Real-time personal attendance percentage gauge.
  - Verification history logs showing timestamp, mode (Face AI / Manual), and confidence score.
  - Student data isolation: Students can only view their own records.
- **Security & Validation:**
  - Password hashing with PBKDF2-HMAC-SHA256 via `werkzeug.security`.
  - Protected session guards (`@login_required`, `@admin_required`, `@student_required`).
  - Strict anti-duplicate protocol to prevent double attendance on the same calendar day.

### 2. 🤖 Live AI Camera Face Recognition
- **Real-Time Detection:** Connects directly to the web camera with low latency.
- **Real-Time HUD Overlays:**
  - **Recognized Students:** Neon green rounded bounding box with Student Name, Roll Number, and Match Confidence %.
  - **Unregistered Faces:** High-visibility red bounding box with "Unknown Person" notification.
- **Dual Camera Operating Modes:**
  1. *Browser Client Mode (WebRTC)*: Cross-platform web stream via HTML5 `getUserMedia`.
  2. *Server Mode (OpenCV)*: High-performance MJPEG live stream direct from OpenCV `cv2.VideoCapture(0)` at `/video_feed`.
- **Audio Feedback:** Web Audio API synthesized two-tone confirmation chime on verified attendance.

### 3. 🎓 Biometric Enrollment & Automated Training
- **Multi-Shot Webcam Biometric Tool:** Rapidly captures 5 face angles directly from the browser camera.
- **Data Augmentation:** Automated illumination balancing and horizontal mirroring for robust recognition under diverse lighting.
- **File Upload Support:** Upload single frontal portrait photos (JPG, PNG).
- **Background Retraining:** The AI model re-trains instantly when new students are enrolled or deleted.

### 4. 📊 Analytics, Reports & Exports
- **Dynamic Metric Cards:** Total Students, Present Today, Late Today, Absent / Pending, and Today's Attendance %.
- **Chart.js Visualizations:** 7-Day Attendance Trend Bar Chart and Department Enrolled Doughnut Chart.
- **One-Click Exports:**
  - **Excel (.xlsx):** Professionally styled workbook with navy headers, status pills (green, amber, red), zebra rows, and auto-adjusted column widths via `openpyxl`.
  - **CSV (.csv):** Standard RFC 4180 format with UTF-8 BOM.

---

## 📂 Project Directory Structure

```
attendance/
├── app.py                              # Flask application controller & routes
├── database.py                         # SQLite schema & database operations
├── face_recognition_module.py          # OpenCV Haar Cascade & LBPH recognition engine
├── attendance.py                       # Business logic, CSV and openpyxl Excel exports
├── haarcascade_frontalface_default.xml # Pre-trained frontal face detector model
├── requirements.txt                    # Project dependencies
├── attendance.db                       # Relational database file (pre-seeded)
├── test_system.py                      # Automated test suite (6 passing test cases)
├── push_to_github.py                   # Automated GitHub deployment helper
├── README.md                           # Documentation
│
├── templates/                          # Jinja2 HTML5 UI templates
│   ├── base.html                       # Global layout with enterprise responsive sidebar
│   ├── auth/
│   │   ├── login.html                  # Tabbed login for Admins & Students
│   │   └── register.html               # Student self-registration portal
│   ├── admin/
│   │   ├── dashboard.html              # Dynamic metrics cards & Chart.js graphs
│   │   ├── students.html               # Student records directory with search & filters
│   │   ├── student_add.html            # Enrollment form & multi-shot webcam tool
│   │   ├── student_edit.html           # Student details and biometric updater
│   │   ├── student_profile.html        # Individual student profile & attendance history
│   │   ├── live_camera.html            # AI Live Camera Face Detection Console
│   │   ├── attendance.html             # Attendance logs & manual override modal
│   │   └── reports.html                # Daily/Weekly/Monthly reports & defaulter alerts
│   └── student/
│       ├── dashboard.html              # Personal attendance percentage & status banner
│       ├── my_attendance.html          # Personal attendance log with CSV/Excel download
│       └── profile.html                # Identity card & password change form
│
├── static/
│   ├── css/
│   │   └── style.css                   # Custom enterprise stylesheet (Navy / Light Blue)
│   └── js/
│       ├── main.js                     # UI interactions, live clock, Chart.js loaders
│       └── camera.js                   # Webcam streaming, canvas HUD, recognition loop
│
└── uploads/
    ├── faces/                          # Face biometric image training samples per student
    └── trained/
        └── face_trainer.yml            # Pre-trained LBPH biometric model weights
```

---

## ⚡ Quick Start & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/sakshijagtap1977-ops/attendance.git
cd attendance
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Automated Tests
```bash
python test_system.py
```
*(All 6 unit and integration test suites pass with 100% success)*

### 4. Start the Application Server
```bash
python app.py
```

Open your browser at:
👉 **`http://127.0.0.1:5000`**

---

## 🔑 Default Credentials

The database comes pre-populated with realistic initial data:

### 🛡️ System Administrator
- **Login Tab:** Administrator
- **Username:** `admin`
- **Password:** `admin123`

### 🎓 Sample Students
- **Login Tab:** Student Portal
- **Student 1 (Ethan Davis):** Roll: `CS202601` | Password: `student123`
- **Student 2 (Sophia Rodriguez):** Roll: `CS202602` | Password: `student123`
- **Student 3 (Aiden Clark):** Roll: `IT202603` | Password: `student123`
- **Student 4 (Emma Watson):** Roll: `EC202604` | Password: `student123`
- **Student 5 (Lucas Miller):** Roll: `ME202605` | Password: `student123`

---

## 📦 Pushing Updates to GitHub

To push changes to the remote repository `https://github.com/sakshijagtap1977-ops/attendance.git`:

```bash
# Using Git CLI
git add .
git commit -m "Update application and documentation"
git push -u origin main
```

Or using the included deployment helper:
```bash
python push_to_github.py <YOUR_GITHUB_TOKEN>
```

---

## 📄 License
This project is licensed under the MIT License - open for educational and commercial use.
