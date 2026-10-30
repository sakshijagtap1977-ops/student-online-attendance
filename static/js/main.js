/**
 * main.js - Core UI Interactivity & Chart.js Visualizations
 * Handles sidebar toggles, real-time clock, data filtering, and dashboard analytics.
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Mobile Sidebar Toggle
    const mobileToggleBtn = document.getElementById('mobileSidebarToggle');
    const sidebar = document.querySelector('.app-sidebar');

    if (mobileToggleBtn && sidebar) {
        mobileToggleBtn.addEventListener('click', function () {
            sidebar.classList.toggle('show');
        });

        // Close sidebar on outside click on mobile
        document.addEventListener('click', function (e) {
            if (window.innerWidth <= 992) {
                if (!sidebar.contains(e.target) && !mobileToggleBtn.contains(e.target)) {
                    sidebar.classList.remove('show');
                }
            }
        });
    }

    // 2. Real-time Topbar Clock
    const liveClockEl = document.getElementById('topbarLiveClock');
    if (liveClockEl) {
        function updateClock() {
            const now = new Date();
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const seconds = String(now.getSeconds()).padStart(2, '0');
            liveClockEl.innerText = `${hours}:${minutes}:${seconds}`;
        }
        updateClock();
        setInterval(updateClock, 1000);
    }

    // 3. Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 6000);
    });

    // 4. Initialize Dashboard Charts if on dashboard page
    initDashboardCharts();
});

/**
 * Loads analytics from /api/dashboard_charts and mounts Chart.js instances
 */
function initDashboardCharts() {
    const weeklyChartEl = document.getElementById('weeklyAttendanceChart');
    const deptChartEl = document.getElementById('deptAttendanceChart');

    if (!weeklyChartEl && !deptChartEl) return;

    fetch('/api/dashboard_charts')
        .then(response => response.json())
        .then(data => {
            // Render Weekly Attendance Line / Bar Chart
            if (weeklyChartEl && data.weekly) {
                const ctx = weeklyChartEl.getContext('2d');
                new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: data.weekly.labels,
                        datasets: [
                            {
                                label: 'Present',
                                data: data.weekly.present,
                                backgroundColor: 'rgba(37, 99, 235, 0.85)',
                                borderColor: '#1d4ed8',
                                borderWidth: 1.5,
                                borderRadius: 6,
                            },
                            {
                                label: 'Late',
                                data: data.weekly.late,
                                backgroundColor: 'rgba(245, 158, 11, 0.85)',
                                borderColor: '#b45309',
                                borderWidth: 1.5,
                                borderRadius: 6,
                            },
                            {
                                label: 'Absent',
                                data: data.weekly.absent,
                                backgroundColor: 'rgba(239, 68, 68, 0.85)',
                                borderColor: '#b91c1c',
                                borderWidth: 1.5,
                                borderRadius: 6,
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'top',
                                labels: {
                                    font: { family: "'Plus Jakarta Sans', sans-serif", size: 12, weight: 600 },
                                    usePointStyle: true,
                                    boxWidth: 8
                                }
                            },
                            tooltip: {
                                backgroundColor: '#0f172a',
                                titleFont: { family: "'Plus Jakarta Sans', sans-serif", weight: 700 },
                                padding: 12,
                                cornerRadius: 8
                            }
                        },
                        scales: {
                            x: {
                                grid: { display: false },
                                ticks: { font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 } }
                            },
                            y: {
                                beginAtZero: true,
                                grid: { color: '#f1f5f9' },
                                ticks: { stepSize: 1, font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 } }
                            }
                        }
                    }
                });
            }

            // Render Department Attendance Doughnut Chart
            if (deptChartEl && data.departments) {
                const ctxDept = deptChartEl.getContext('2d');
                new Chart(ctxDept, {
                    type: 'doughnut',
                    data: {
                        labels: data.departments.departments,
                        datasets: [{
                            data: data.departments.total_students,
                            backgroundColor: [
                                '#2563eb', // Blue
                                '#38bdf8', // Sky
                                '#10b981', // Emerald
                                '#f59e0b', // Amber
                                '#8b5cf6', // Violet
                                '#ec4899'  // Pink
                            ],
                            borderWidth: 2,
                            borderColor: '#ffffff',
                            hoverOffset: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: {
                                    font: { family: "'Plus Jakarta Sans', sans-serif", size: 11, weight: 600 },
                                    usePointStyle: true,
                                    padding: 14
                                }
                            },
                            tooltip: {
                                backgroundColor: '#0f172a',
                                padding: 12,
                                cornerRadius: 8,
                                callbacks: {
                                    label: function (context) {
                                        return ` ${context.label}: ${context.raw} Students`;
                                    }
                                }
                            }
                        },
                        cutout: '68%'
                    }
                });
            }
        })
        .catch(err => {
            console.error('Failed to load dashboard charts data:', err);
        });
}
