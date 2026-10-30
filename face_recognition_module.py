"""
face_recognition_module.py - AI Face Detection and Facial Recognition Engine
Utilizes OpenCV's Haar Feature-based Cascade Classifiers and LBPH (Local Binary Patterns Histograms)
Face Recognizer for robust, real-time facial biometric identification and automatic attendance tracking.
"""

import os
import cv2
import numpy as np
import base64
import time
from PIL import Image
import database

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CASCADE_PATH = os.path.join(BASE_DIR, 'haarcascade_frontalface_default.xml')
FACES_DIR = os.path.join(BASE_DIR, 'uploads', 'faces')
TRAINER_DIR = os.path.join(BASE_DIR, 'uploads', 'trained')
TRAINER_FILE = os.path.join(TRAINER_DIR, 'face_trainer.yml')

# Ensure directories exist
os.makedirs(FACES_DIR, exist_ok=True)
os.makedirs(TRAINER_DIR, exist_ok=True)

# Confidence threshold for LBPH Face Recognizer
# In LBPH, lower distance means better match. Distance <= 75 is considered a valid match.
LBPH_DISTANCE_THRESHOLD = 75.0

class FaceEngine:
    def __init__(self):
        self.cascade = cv2.CascadeClassifier(CASCADE_PATH)
        if self.cascade.empty():
            print(f"[ERROR] Could not load Haar cascade from {CASCADE_PATH}")
        else:
            print("[INFO] Haar Cascade loaded successfully.")
            
        self.recognizer = cv2.face.LBPHFaceRecognizer_create(radius=1, neighbors=8, grid_x=8, grid_y=8)
        self.is_trained = False
        self.load_model()

    def load_model(self):
        """Loads trained LBPH model if it exists."""
        if os.path.exists(TRAINER_FILE) and os.path.getsize(TRAINER_FILE) > 0:
            try:
                self.recognizer.read(TRAINER_FILE)
                self.is_trained = True
                print(f"[INFO] LBPH Face Recognizer loaded from {TRAINER_FILE}")
            except Exception as e:
                print(f"[WARNING] Could not load existing trainer file: {e}")
                self.is_trained = False
        else:
            print("[INFO] No existing face trainer file found. Training required after face registration.")
            self.is_trained = False

    def detect_faces(self, frame):
        """
        Detects faces in a BGR frame.
        Returns: list of (x, y, w, h) coordinates and the grayscale equalized frame.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Apply histogram equalization for illumination invariance
        gray_eq = cv2.equalizeHist(gray)
        faces = self.cascade.detectMultiScale(
            gray_eq,
            scaleFactor=1.15,
            minNeighbors=5,
            minSize=(80, 80),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        return faces, gray_eq

    def crop_and_standardize_face(self, gray_img, bbox, target_size=(200, 200)):
        """Crops face with optional margin and normalizes to standard size."""
        x, y, w, h = bbox
        # Add slight margin around face (10%)
        margin_x = int(w * 0.1)
        margin_y = int(h * 0.1)
        
        h_img, w_img = gray_img.shape[:2]
        x1 = max(0, x - margin_x)
        y1 = max(0, y - margin_y)
        x2 = min(w_img, x + w + margin_x)
        y2 = min(h_img, y + h + margin_y)
        
        face_roi = gray_img[y1:y2, x1:x2]
        if face_roi.size == 0:
            face_roi = gray_img[y:y+h, x:x+w]
            
        face_resized = cv2.resize(face_roi, target_size, interpolation=cv2.INTER_CUBIC)
        return face_resized

    def register_student_faces(self, student_id, roll_number, image_sources):
        """
        Processes and stores multiple face snapshots for a student, then re-trains the model.
        image_sources: list of numpy BGR frames, base64 strings, or file paths.
        Returns: (success: bool, count: int, message: str)
        """
        student_folder = os.path.join(FACES_DIR, f"{student_id}_{roll_number}")
        os.makedirs(student_folder, exist_ok=True)

        saved_count = 0
        primary_photo_path = None

        for idx, src in enumerate(image_sources):
            frame = None
            if isinstance(src, str):
                if src.startswith('data:image'):
                    # Base64 string
                    header, encoded = src.split(',', 1)
                    img_data = base64.b64decode(encoded)
                    nparr = np.frombuffer(img_data, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                elif os.path.isfile(src):
                    frame = cv2.imread(src)
            elif isinstance(src, np.ndarray):
                frame = src

            if frame is None:
                continue

            faces, gray_eq = self.detect_faces(frame)
            if len(faces) == 0:
                # If cascade did not find face in this angle, fall back to center crop
                h, w = frame.shape[:2]
                min_dim = min(h, w)
                cx, cy = w // 2, h // 2
                x = max(0, cx - min_dim // 2)
                y = max(0, cy - min_dim // 2)
                faces = [(x, y, min_dim, min_dim)]
                gray_eq = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Take the largest face
            faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
            best_face = faces[0]

            face_norm = self.crop_and_standardize_face(gray_eq, best_face)
            file_name = f"sample_{idx + 1}_{int(time.time()*1000)}.jpg"
            file_path = os.path.join(student_folder, file_name)
            cv2.imwrite(file_path, face_norm)
            saved_count += 1

            if primary_photo_path is None:
                # Save first sample as primary photo
                rel_path = f"faces/{student_id}_{roll_number}/{file_name}"
                primary_photo_path = rel_path
                database.save_face_encoding(student_id, roll_number, rel_path, None)

            # Data Augmentation to enhance recognition under varying illumination & angles
            # 1. Horizontal flip
            flip = cv2.flip(face_norm, 1)
            flip_name = f"sample_{idx + 1}_flip_{int(time.time()*1000)}.jpg"
            cv2.imwrite(os.path.join(student_folder, flip_name), flip)
            saved_count += 1

            # 2. Slight brightness variation
            bright = cv2.convertScaleAbs(face_norm, alpha=1.1, beta=15)
            bright_name = f"sample_{idx + 1}_bright_{int(time.time()*1000)}.jpg"
            cv2.imwrite(os.path.join(student_folder, bright_name), bright)
            saved_count += 1

        if saved_count > 0:
            # Retrain model with all registered faces
            train_success, train_msg = self.train_model()
            return True, saved_count, f"Saved {saved_count} face training samples. {train_msg}"
        else:
            return False, 0, "No clear faces were detected in the provided images."

    def train_model(self):
        """
        Scans all student folders in FACES_DIR and trains LBPH Face Recognizer.
        Returns: (success: bool, message: str)
        """
        face_samples = []
        ids = []

        if not os.path.exists(FACES_DIR):
            return False, "Faces directory does not exist."

        for entry in os.listdir(FACES_DIR):
            student_path = os.path.join(FACES_DIR, entry)
            if not os.path.isdir(student_path):
                continue

            # Directory format: {student_id}_{roll_number}
            try:
                student_id = int(entry.split('_')[0])
            except (ValueError, IndexError):
                continue

            for fname in os.listdir(student_path):
                if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                    img_path = os.path.join(student_path, fname)
                    img = Image.open(img_path).convert('L')
                    img_np = np.array(img, 'uint8')
                    if img_np.shape != (200, 200):
                        img_np = cv2.resize(img_np, (200, 200))
                    face_samples.append(img_np)
                    ids.append(student_id)

        if len(face_samples) == 0:
            self.is_trained = False
            return False, "No face samples found to train model."

        try:
            self.recognizer = cv2.face.LBPHFaceRecognizer_create(radius=1, neighbors=8, grid_x=8, grid_y=8)
            self.recognizer.train(face_samples, np.array(ids))
            self.recognizer.write(TRAINER_FILE)
            self.is_trained = True
            unique_students = len(set(ids))
            return True, f"Model trained with {len(face_samples)} samples across {unique_students} student(s)."
        except Exception as e:
            return False, f"Failed to train face recognizer: {str(e)}"

    def recognize_face(self, face_gray):
        """
        Recognizes a standardized face ROI.
        Returns: (student_id: int or None, confidence_pct: float, distance: float)
        """
        if not self.is_trained:
            return None, 0.0, 999.0

        try:
            face_resized = cv2.resize(face_gray, (200, 200))
            predicted_id, distance = self.recognizer.predict(face_resized)
            
            # Confidence calculation:
            # LBPH distance ranges roughly from 0 (perfect) to 120+ (unrelated)
            confidence_pct = max(0.0, min(100.0, round(100.0 - (distance * 0.7), 1)))

            if distance <= LBPH_DISTANCE_THRESHOLD:
                return predicted_id, confidence_pct, round(distance, 1)
            else:
                return None, confidence_pct, round(distance, 1)
        except Exception as e:
            print(f"[ERROR] Recognition prediction failed: {e}")
            return None, 0.0, 999.0

    def process_frame(self, frame, auto_mark=True):
        """
        Analyzes a single video frame, detects all faces, recognizes students,
        optionally records attendance, and returns structured metadata + annotated frame.
        """
        faces, gray_eq = self.detect_faces(frame)
        results = []
        annotated_frame = frame.copy()

        for (x, y, w, h) in faces:
            face_roi = gray_eq[y:y+h, x:x+w]
            student_id, conf, dist = self.recognize_face(face_roi)

            person_info = {
                'box': [int(x), int(y), int(w), int(h)],
                'recognized': False,
                'student_id': None,
                'name': 'Unknown Person',
                'roll_number': 'N/A',
                'department': 'N/A',
                'confidence': conf,
                'distance': dist,
                'attendance_marked': False,
                'attendance_message': ''
            }

            if student_id is not None:
                student = database.get_student_by_id(student_id)
                if student:
                    person_info['recognized'] = True
                    person_info['student_id'] = student['id']
                    person_info['name'] = student['name']
                    person_info['roll_number'] = student['roll_number']
                    person_info['department'] = student['department']

                    # Check or mark attendance
                    if auto_mark:
                        marked, msg, record = database.mark_attendance(
                            student_id=student['id'],
                            roll_number=student['roll_number'],
                            status='Present',
                            verification_mode='Face Recognition',
                            confidence_score=conf,
                            notes=f'Auto-recognized with confidence {conf}%'
                        )
                        person_info['attendance_marked'] = marked
                        person_info['attendance_message'] = msg

                    # Draw green bounding box & label
                    color = (0, 200, 80) # Clean emerald green
                    cv2.rectangle(annotated_frame, (x, y), (x+w, y+h), color, 2)
                    
                    label_title = f"{student['name']} ({conf}%)"
                    label_sub = f"Roll: {student['roll_number']}"
                    
                    # Background pill for text
                    cv2.rectangle(annotated_frame, (x, y - 55), (x + max(w, 220), y), (15, 23, 42), -1)
                    cv2.putText(annotated_frame, label_title, (x + 8, y - 32), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 2)
                    cv2.putText(annotated_frame, label_sub, (x + 8, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (56, 189, 248), 1)
            else:
                # Unrecognized face - draw warning red box
                color = (40, 40, 230) # High-visibility red
                cv2.rectangle(annotated_frame, (x, y), (x+w, y+h), color, 2)
                
                cv2.rectangle(annotated_frame, (x, y - 35), (x + max(w, 170), y), (15, 23, 42), -1)
                cv2.putText(annotated_frame, "Unknown Person", (x + 8, y - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

            results.append(person_info)

        return results, annotated_frame

# Global singleton engine
engine = FaceEngine()

class CameraController:
    """Manages OpenCV live camera capture thread-safely."""
    def __init__(self):
        self.camera = None
        self.is_running = False

    def start_camera(self, camera_index=0):
        if not self.is_running or self.camera is None:
            self.camera = cv2.VideoCapture(camera_index)
            if self.camera.isOpened():
                self.is_running = True
                return True
            else:
                self.camera = None
                self.is_running = False
                return False
        return True

    def stop_camera(self):
        self.is_running = False
        if self.camera is not None:
            try:
                self.camera.release()
            except Exception:
                pass
            self.camera = None

    def get_frame(self):
        if not self.is_running or self.camera is None:
            return None
        success, frame = self.camera.read()
        if not success:
            return None
        return frame

camera_controller = CameraController()
