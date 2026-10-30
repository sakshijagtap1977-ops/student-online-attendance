"""
test_system.py - End-to-End Automated Test Suite for Student Attendance System
Validates database integrity, face recognition, reporting, authentication, and HTTP routes.
"""

import os
import cv2
import numpy as np
import base64
import unittest
from werkzeug.security import check_password_hash

import database
import attendance
import face_recognition_module
from app import app

class TestAttendanceSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.init_db()
        cls.client = app.test_client()

    def test_01_database_seed_and_metrics(self):
        """Verify seeded students and dashboard metric calculations."""
        stats = database.get_dashboard_metrics()
        self.assertGreaterEqual(stats['total_students'], 5)
        self.assertIn('today_percentage', stats)
        self.assertIn('overall_percentage', stats)

    def test_02_student_crud(self):
        """Test adding, querying, and updating a student."""
        test_roll = "TEST9999"
        sid, err = database.add_student(
            roll_number=test_roll,
            name="Test Candidate",
            email="test.candidate@university.edu",
            department="Computer Science",
            year="2nd Year",
            initial_password="secretpassword"
        )
        self.assertIsNotNone(sid, f"Student creation failed: {err}")

        # Duplicate roll number check
        dup_id, dup_err = database.add_student(
            roll_number=test_roll,
            name="Duplicate Candidate",
            email="dup@university.edu",
            department="Computer Science",
            year="1st Year"
        )
        self.assertIsNone(dup_id)
        self.assertIn("already exists", dup_err)

        # Retrieve and verify student
        s = database.get_student_by_id(sid)
        self.assertEqual(s['name'], "Test Candidate")

        # Update student
        ok, upd_err = database.update_student(
            student_id=sid,
            name="Test Candidate Renamed",
            email="test.renamed@university.edu",
            department="Information Technology",
            year="3rd Year",
            gender="Other",
            phone="+123456789"
        )
        self.assertTrue(ok)
        s_updated = database.get_student_by_id(sid)
        self.assertEqual(s_updated['name'], "Test Candidate Renamed")

        # Clean up test student
        del_ok, _ = database.delete_student(sid)
        self.assertTrue(del_ok)

    def test_03_attendance_marking_and_duplicate_prevention(self):
        """Verify attendance marking and duplicate prevention on same day."""
        students = database.get_all_students()
        target_student = students[0]
        test_date = "2026-12-25" # Far date to avoid polluting today's stats

        # 1. Mark attendance
        ok, msg, rec = database.mark_attendance(
            student_id=target_student['id'],
            roll_number=target_student['roll_number'],
            status='Present',
            verification_mode='Face Recognition',
            confidence_score=96.4,
            att_date=test_date
        )
        self.assertTrue(ok)
        self.assertIn("successfully", msg)

        # 2. Attempt duplicate on same date
        dup_ok, dup_msg, _ = database.mark_attendance(
            student_id=target_student['id'],
            roll_number=target_student['roll_number'],
            status='Present',
            verification_mode='Face Recognition',
            confidence_score=95.0,
            att_date=test_date
        )
        self.assertFalse(dup_ok)
        self.assertIn("already marked", dup_msg.lower())

        # Clean up test record
        if rec and 'id' in rec:
            database.delete_attendance_record(rec['id'])

    def test_04_reports_export(self):
        """Verify CSV and Excel report generation."""
        data = attendance.get_report_data('all')
        self.assertGreater(len(data), 0)

        csv_bytes = attendance.export_attendance_csv(data)
        self.assertGreater(len(csv_bytes), 100)
        self.assertTrue(csv_bytes.startswith(b'\xef\xbb\xbfRecord ID' or b'Record ID'))

        excel_bytes = attendance.export_attendance_excel(data)
        self.assertGreater(len(excel_bytes), 1000)
        # Excel zip header begins with PK
        self.assertTrue(excel_bytes.startswith(b'PK'))

    def test_05_admin_authentication_and_routes(self):
        """Test Admin login and all protected admin pages."""
        # 1. Test invalid login
        res_fail = self.client.post('/login', data={'user_type': 'admin', 'username': 'admin', 'password': 'wrongpassword'})
        self.assertIn(b'Invalid', res_fail.data)

        # 2. Test successful admin login
        res_login = self.client.post('/login', data={'user_type': 'admin', 'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        self.assertEqual(res_login.status_code, 200)
        self.assertIn(b'Executive Attendance Dashboard', res_login.data)

        # 3. Test admin dashboard
        res_dash = self.client.get('/admin/dashboard')
        self.assertEqual(res_dash.status_code, 200)
        self.assertIn(b'Total Students', res_dash.data)

        # 4. Test students directory
        res_students = self.client.get('/admin/students')
        self.assertEqual(res_students.status_code, 200)
        self.assertIn(b'Student Directory', res_students.data)

        # 5. Test live camera page
        res_cam = self.client.get('/admin/camera')
        self.assertEqual(res_cam.status_code, 200)
        self.assertIn(b'Real-time Biometric Camera Stream', res_cam.data)

        # 6. Test attendance logs
        res_att = self.client.get('/admin/attendance')
        self.assertEqual(res_att.status_code, 200)
        self.assertIn(b'Attendance Registry', res_att.data)

        # 7. Test reports page
        res_rep = self.client.get('/admin/reports')
        self.assertEqual(res_rep.status_code, 200)
        self.assertIn(b'Report Generator', res_rep.data)

        # 8. Test export endpoints
        res_csv = self.client.get('/export/attendance/csv')
        self.assertEqual(res_csv.status_code, 200)
        self.assertEqual(res_csv.content_type, 'text/csv; charset=utf-8')

        res_xlsx = self.client.get('/export/attendance/excel')
        self.assertEqual(res_xlsx.status_code, 200)

        # 9. Test API recognize frame endpoint with synthetic image
        test_frame = np.zeros((300, 300, 3), dtype=np.uint8)
        _, buf = cv2.imencode('.jpg', test_frame)
        b64_img = 'data:image/jpeg;base64,' + base64.b64encode(buf.tobytes()).decode('utf-8')

        res_api = self.client.post('/api/recognize_frame', json={'image': b64_img, 'auto_mark': False})
        self.assertEqual(res_api.status_code, 200)
        json_data = res_api.get_json()
        self.assertTrue(json_data['success'])
        self.assertEqual(json_data['faces_detected'], 0) # Blank image = 0 faces

        # Logout
        self.client.get('/logout')

    def test_06_student_portal_and_access_control(self):
        """Test Student authentication and role-based data isolation."""
        # Login as student CS202601
        res = self.client.post('/login', data={'user_type': 'student', 'username': 'CS202601', 'password': 'student123'}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Ethan Davis', res.data)

        # Access student personal views
        res_dash = self.client.get('/student/dashboard')
        self.assertEqual(res_dash.status_code, 200)

        res_att = self.client.get('/student/my-attendance')
        self.assertEqual(res_att.status_code, 200)

        res_prof = self.client.get('/student/profile')
        self.assertEqual(res_prof.status_code, 200)

        # Security check: student should NOT be able to access admin console
        res_forbidden = self.client.get('/admin/dashboard', follow_redirects=True)
        self.assertIn(b'Access restricted to System Administrators', res_forbidden.data)

        # Student CSV export should only contain their own records
        res_csv = self.client.get('/export/attendance/csv')
        self.assertEqual(res_csv.status_code, 200)
        csv_text = res_csv.data.decode('utf-8')
        # All rows should belong to Ethan Davis / CS202601
        self.assertIn('CS202601', csv_text)
        self.assertNotIn('CS202602', csv_text)

        self.client.get('/logout')

if __name__ == '__main__':
    unittest.main()
