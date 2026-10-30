/**
 * camera.js - Web Camera Stream, Real-time Face Detection, and Biometric Capture
 * Connects browser webcam to Flask AI backend for live facial recognition attendance marking.
 */

class AttendanceCameraManager {
    constructor() {
        this.video = document.getElementById('cameraVideo');
        this.canvas = document.getElementById('cameraCanvas');
        this.ctx = this.canvas ? this.canvas.getContext('2d') : null;
        
        this.startBtn = document.getElementById('btnStartCamera');
        this.stopBtn = document.getElementById('btnStopCamera');
        this.statusPill = document.getElementById('cameraStatusPill');
        this.cameraModeSelect = document.getElementById('cameraModeSelect');
        this.streamContainer = document.getElementById('cameraStreamContainer');
        this.emptyState = document.getElementById('cameraEmptyState');
        this.scanline = document.getElementById('cameraScanline');

        this.stream = null;
        this.isProcessing = false;
        this.processingInterval = null;
        this.intervalMs = 650; // Process frame every 650ms for low latency
        this.audioCtx = null;

        // Tracking last recognized roll numbers to prevent sound flood
        this.recentNotifications = new Map();

        this.initEventListeners();
    }

    initEventListeners() {
        if (this.startBtn) {
            this.startBtn.addEventListener('click', () => this.startLiveAttendance());
        }
        if (this.stopBtn) {
            this.stopBtn.addEventListener('click', () => this.stopLiveAttendance());
        }
        if (this.cameraModeSelect) {
            this.cameraModeSelect.addEventListener('change', () => this.handleModeChange());
        }
    }

    playChime(type = 'success') {
        try {
            if (!this.audioCtx) {
                this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            }
            if (this.audioCtx.state === 'suspended') {
                this.audioCtx.resume();
            }

            const osc = this.audioCtx.createOscillator();
            const gain = this.audioCtx.createGain();
            osc.connect(gain);
            gain.connect(this.audioCtx.destination);

            if (type === 'success') {
                // Pleasant ascending two-tone chime
                osc.type = 'sine';
                osc.frequency.setValueAtTime(587.33, this.audioCtx.currentTime); // D5
                osc.frequency.setValueAtTime(880.00, this.audioCtx.currentTime + 0.12); // A5
                gain.gain.setValueAtTime(0.18, this.audioCtx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, this.audioCtx.currentTime + 0.45);
                osc.start();
                osc.stop(this.audioCtx.currentTime + 0.45);
            } else {
                // Warning low tone
                osc.type = 'triangle';
                osc.frequency.setValueAtTime(320, this.audioCtx.currentTime);
                gain.gain.setValueAtTime(0.12, this.audioCtx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, this.audioCtx.currentTime + 0.3);
                osc.start();
                osc.stop(this.audioCtx.currentTime + 0.3);
            }
        } catch (e) {
            console.log('Audio chime not supported or muted');
        }
    }

    async startLiveAttendance() {
        const mode = this.cameraModeSelect ? this.cameraModeSelect.value : 'webrtc';

        if (mode === 'opencv') {
            // Direct OpenCV VideoCapture backend stream
            this.startOpenCVStream();
            return;
        }

        // WebRTC HTML5 getUserMedia mode
        try {
            this.updateStatus('Starting Camera...', 'warning');

            const constraints = {
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: 'user'
                },
                audio: false
            };

            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            this.video.srcObject = this.stream;
            await this.video.play();

            // Set canvas size to video aspect ratio
            this.video.addEventListener('loadedmetadata', () => {
                this.canvas.width = this.video.videoWidth;
                this.canvas.height = this.video.videoHeight;
            });

            this.emptyState.style.display = 'none';
            this.video.style.display = 'block';
            this.canvas.style.display = 'block';
            if (this.scanline) this.scanline.style.display = 'block';

            this.startBtn.classList.add('d-none');
            this.stopBtn.classList.remove('d-none');

            this.updateStatus('Camera Active & Detecting', 'success');
            this.isProcessing = true;

            // Start continuous frame processing loop
            this.processingInterval = setInterval(() => this.processWebcamFrame(), this.intervalMs);

        } catch (err) {
            console.error('Camera access failed:', err);
            this.updateStatus('Camera Permission Denied', 'danger');
            Swal.fire({
                icon: 'error',
                title: 'Camera Access Error',
                text: 'Could not access the web camera. Please check your browser camera permissions or try switching to Server OpenCV camera mode.',
                confirmButtonColor: '#2563eb'
            });
        }
    }

    stopLiveAttendance() {
        this.isProcessing = false;
        if (this.processingInterval) {
            clearInterval(this.processingInterval);
            this.processingInterval = null;
        }

        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }

        if (this.ctx && this.canvas) {
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        }

        if (this.video) {
            this.video.srcObject = null;
            this.video.style.display = 'none';
        }

        const mjpegImg = document.getElementById('openCVMjpegStream');
        if (mjpegImg) {
            mjpegImg.remove();
            fetch('/api/camera_control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'stop' })
            }).catch(console.error);
        }

        this.canvas.style.display = 'none';
        if (this.scanline) this.scanline.style.display = 'none';
        this.emptyState.style.display = 'block';

        this.stopBtn.classList.add('d-none');
        this.startBtn.classList.remove('d-none');
        this.updateStatus('Camera Inactive', 'secondary');
    }

    startOpenCVStream() {
        this.emptyState.style.display = 'none';
        this.video.style.display = 'none';
        this.canvas.style.display = 'none';
        if (this.scanline) this.scanline.style.display = 'block';

        let mjpegImg = document.getElementById('openCVMjpegStream');
        if (!mjpegImg) {
            mjpegImg = document.createElement('img');
            mjpegImg.id = 'openCVMjpegStream';
            mjpegImg.className = 'camera-video';
            this.streamContainer.appendChild(mjpegImg);
        }

        fetch('/api/camera_control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'start' })
        })
        .then(() => {
            mjpegImg.src = '/video_feed?' + new Date().getTime();
            this.startBtn.classList.add('d-none');
            this.stopBtn.classList.remove('d-none');
            this.updateStatus('OpenCV Backend Stream Active', 'success');
        })
        .catch(err => {
            console.error('OpenCV camera error:', err);
            this.updateStatus('OpenCV Camera Failed', 'danger');
        });
    }

    handleModeChange() {
        this.stopLiveAttendance();
    }

    async processWebcamFrame() {
        if (!this.isProcessing || !this.video || this.video.readyState !== 4) return;

        // Draw current video frame to an offscreen canvas
        const offCanvas = document.createElement('canvas');
        offCanvas.width = this.video.videoWidth || 640;
        offCanvas.height = this.video.videoHeight || 480;
        const offCtx = offCanvas.getContext('2d');
        offCtx.drawImage(this.video, 0, 0, offCanvas.width, offCanvas.height);

        const base64Data = offCanvas.toDataURL('image/jpeg', 0.82);

        try {
            const response = await fetch('/api/recognize_frame', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image: base64Data, auto_mark: true })
            });

            const data = await response.json();
            if (data.success) {
                this.renderDetectionBoxes(data.results, offCanvas.width, offCanvas.height);
                this.handleAttendanceEvents(data.results);
            }
        } catch (err) {
            console.warn('Frame recognition request error:', err);
        }
    }

    renderDetectionBoxes(results, sourceWidth, sourceHeight) {
        if (!this.ctx || !this.canvas) return;

        // Clear canvas overlay
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Scale factors if display differs from source resolution
        const scaleX = this.canvas.width / sourceWidth;
        const scaleY = this.canvas.height / sourceHeight;

        results.forEach(res => {
            const [x, y, w, h] = res.box;
            const drawX = x * scaleX;
            const drawY = y * scaleY;
            const drawW = w * scaleX;
            const drawH = h * scaleY;

            if (res.recognized) {
                // Green neon frame for recognized student
                this.ctx.strokeStyle = '#10b981';
                this.ctx.lineWidth = 3;
                this.drawRoundedRect(this.ctx, drawX, drawY, drawW, drawH, 10);
                this.ctx.stroke();

                // Pill label
                const label = `${res.name} (${res.confidence}%)`;
                const subLabel = `Roll: ${res.roll_number}`;
                
                this.ctx.fillStyle = 'rgba(15, 23, 42, 0.9)';
                this.drawRoundedRect(this.ctx, drawX, Math.max(0, drawY - 54), Math.max(drawW, 210), 48, 6);
                this.ctx.fill();

                this.ctx.fillStyle = '#ffffff';
                this.ctx.font = 'bold 14px "Plus Jakarta Sans", sans-serif';
                this.ctx.fillText(label, drawX + 10, Math.max(16, drawY - 32));

                this.ctx.fillStyle = '#38bdf8';
                this.ctx.font = '500 12px "JetBrains Mono", monospace';
                this.ctx.fillText(subLabel, drawX + 10, Math.max(32, drawY - 14));

            } else {
                // High-visibility red frame for Unknown Person
                this.ctx.strokeStyle = '#ef4444';
                this.ctx.lineWidth = 3;
                this.drawRoundedRect(this.ctx, drawX, drawY, drawW, drawH, 10);
                this.ctx.stroke();

                this.ctx.fillStyle = 'rgba(239, 68, 68, 0.9)';
                this.drawRoundedRect(this.ctx, drawX, Math.max(0, drawY - 34), Math.max(drawW, 160), 30, 6);
                this.ctx.fill();

                this.ctx.fillStyle = '#ffffff';
                this.ctx.font = 'bold 13px "Plus Jakarta Sans", sans-serif';
                this.ctx.fillText('Unknown Person', drawX + 10, Math.max(16, drawY - 14));
            }
        });
    }

    drawRoundedRect(ctx, x, y, width, height, radius) {
        ctx.beginPath();
        ctx.moveTo(x + radius, y);
        ctx.lineTo(x + width - radius, y);
        ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
        ctx.lineTo(x + width, y + height - radius);
        ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
        ctx.lineTo(x + radius, y + height);
        ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
        ctx.lineTo(x, y + radius);
        ctx.quadraticCurveTo(x, y, x + radius, y);
        ctx.closePath();
    }

    handleAttendanceEvents(results) {
        const now = Date.now();
        const cooldownMs = 6000; // Only alert once every 6 seconds per person

        results.forEach(res => {
            if (res.recognized) {
                const lastNotified = this.recentNotifications.get(res.roll_number) || 0;

                if (res.attendance_marked && (now - lastNotified > cooldownMs)) {
                    this.recentNotifications.set(res.roll_number, now);
                    this.playChime('success');
                    this.showAttendanceToast(res, true);
                    this.prependLiveAttendanceRow(res);
                } else if (!res.attendance_marked && res.attendance_message.includes('already') && (now - lastNotified > cooldownMs)) {
                    this.recentNotifications.set(res.roll_number, now);
                    this.showAttendanceToast(res, false);
                }
            }
        });
    }

    showAttendanceToast(student, isNewMarking) {
        const title = isNewMarking ? 'Attendance Marked!' : 'Already Recorded';
        const icon = isNewMarking ? 'success' : 'info';
        const msg = `${student.name} (${student.roll_number}) — ${student.attendance_message}`;

        const Toast = Swal.mixin({
            toast: true,
            position: 'top-end',
            showConfirmButton: false,
            timer: 4500,
            timerProgressBar: true,
            didOpen: (toast) => {
                toast.addEventListener('mouseenter', Swal.stopTimer);
                toast.addEventListener('mouseleave', Swal.resumeTimer);
            }
        });

        Toast.fire({
            icon: icon,
            title: title,
            text: msg
        });
    }

    prependLiveAttendanceRow(student) {
        const tableBody = document.getElementById('liveAttendanceStreamBody');
        if (!tableBody) return;

        const row = document.createElement('tr');
        row.className = 'table-success animate__animated animate__fadeIn';
        const currentTime = new Date().toLocaleTimeString();

        row.innerHTML = `
            <td>
                <span class="badge bg-primary">${student.roll_number}</span>
            </td>
            <td><strong>${student.name}</strong></td>
            <td>${student.department}</td>
            <td>${currentTime}</td>
            <td><span class="badge-status badge-present"><i class="fas fa-check-circle"></i> Present</span></td>
            <td><span class="badge bg-light text-dark">${student.confidence}%</span></td>
        `;

        tableBody.insertBefore(row, tableBody.firstChild);

        // Update dashboard present counter if present
        const counter = document.getElementById('statPresentCount');
        if (counter) {
            const currentVal = parseInt(counter.innerText) || 0;
            counter.innerText = currentVal + 1;
        }
    }

    updateStatus(text, variant = 'primary') {
        if (!this.statusPill) return;
        this.statusPill.innerHTML = `
            <span class="live-pulse" style="background-color: var(--${variant})"></span>
            <span>${text}</span>
        `;
    }
}

// -------------------------------------------------------------
// STUDENT FACE REGISTRATION MULTI-SHOT CAMERA CAPTURE TOOL
// -------------------------------------------------------------

class StudentFaceCaptureTool {
    constructor() {
        this.modalEl = document.getElementById('faceCaptureModal');
        this.videoEl = document.getElementById('captureVideo');
        this.canvasEl = document.getElementById('captureCanvas');
        this.previewGallery = document.getElementById('snapshotPreviewGallery');
        this.hiddenContainer = document.getElementById('hiddenSnapshotsContainer');
        this.captureBtn = document.getElementById('btnTakeSnapshots');
        this.statusText = document.getElementById('captureProgressText');

        this.stream = null;
        this.snapshots = [];

        if (this.captureBtn) {
            this.captureBtn.addEventListener('click', () => this.runMultiSnapshotSequence());
        }

        if (this.modalEl) {
            this.modalEl.addEventListener('shown.bs.modal', () => this.startCaptureCamera());
            this.modalEl.addEventListener('hidden.bs.modal', () => this.stopCaptureCamera());
        }
    }

    async startCaptureCamera() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { width: 640, height: 480, facingMode: 'user' }
            });
            this.videoEl.srcObject = this.stream;
            await this.videoEl.play();
        } catch (e) {
            alert('Could not access camera for face capture: ' + e.message);
        }
    }

    stopCaptureCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(t => t.stop());
            this.stream = null;
        }
    }

    async runMultiSnapshotSequence() {
        this.captureBtn.disabled = true;
        this.snapshots = [];
        this.previewGallery.innerHTML = '';
        this.hiddenContainer.innerHTML = '';

        const totalShots = 5;

        for (let i = 1; i <= totalShots; i++) {
            this.statusText.innerText = `Capturing sample ${i} of ${totalShots}... Hold steady and look directly at the camera`;
            
            // 300ms countdown pause
            await new Promise(r => setTimeout(r, 450));

            const canvas = document.createElement('canvas');
            canvas.width = this.videoEl.videoWidth || 640;
            canvas.height = this.videoEl.videoHeight || 480;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(this.videoEl, 0, 0, canvas.width, canvas.height);

            const b64 = canvas.toDataURL('image/jpeg', 0.9);
            this.snapshots.push(b64);

            // Add thumbnail to UI preview gallery
            const thumb = document.createElement('img');
            thumb.src = b64;
            thumb.className = 'snapshot-thumb';
            this.previewGallery.appendChild(thumb);

            // Add hidden input to form
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'webcam_snapshots[]';
            input.value = b64;
            this.hiddenContainer.appendChild(input);
        }

        this.statusText.innerText = `Successfully captured ${totalShots} biometric samples!`;
        this.captureBtn.disabled = false;
        
        // Show success notification
        Swal.fire({
            icon: 'success',
            title: 'Face Samples Captured!',
            text: `${totalShots} face angles recorded. Submit the registration form to finalize AI model training.`,
            confirmButtonColor: '#2563eb'
        });
    }
}

// Global initialization
window.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('cameraVideo')) {
        window.cameraManager = new AttendanceCameraManager();
    }
    if (document.getElementById('faceCaptureModal')) {
        window.faceCaptureTool = new StudentFaceCaptureTool();
    }
});
