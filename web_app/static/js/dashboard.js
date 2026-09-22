/**
 * LinkedIn AI Growth Hub - Client Interaction Controller
 */

// Active state
let activeScheduleTimes = [];
let isPublishing = false;

document.addEventListener('DOMContentLoaded', () => {
    initScheduleChips();
    pollSystemStatus();
    // Poll status every 12 seconds
    setInterval(pollSystemStatus, 12000);
});

function initScheduleChips() {
    const chips = document.querySelectorAll('.time-chip');
    activeScheduleTimes = Array.from(chips).map(c => c.getAttribute('data-time')).filter(Boolean);
}

// 1. Live System Status Polling
async function pollSystemStatus() {
    if (isPublishing) return;
    try {
        const resp = await fetch('/api/status');
        const data = await resp.json();

        // Update Next Run
        const nextDisplay = document.getElementById('next-run-display');
        if (nextDisplay) {
            nextDisplay.textContent = data.next_run ? data.next_run : 'مجدول حسب الأوقات المحددة';
        }

        // Update Last Run
        const lastDisplay = document.getElementById('last-run-display');
        if (lastDisplay && data.last_run) {
            lastDisplay.textContent = data.last_run;
        }

        // Update Toggle
        const toggle = document.getElementById('scheduler-toggle');
        if (toggle && toggle.checked !== data.scheduler_enabled) {
            toggle.checked = data.scheduler_enabled;
        }

        // Update LinkedIn Connection Badge
        const lkBadge = document.getElementById('linkedin-status-badge');
        if (lkBadge) {
            if (data.linkedin_connected) {
                lkBadge.className = 'status-badge badge-success';
                lkBadge.querySelector('.badge-label').textContent = 'LinkedIn API: متصل وآمن';
            } else {
                lkBadge.className = 'status-badge badge-warning';
                lkBadge.querySelector('.badge-label').textContent = 'LinkedIn: يتطلب الربط';
            }
        }
    } catch (e) {
        console.warn('Status poll failed:', e);
    }
}

// 2. Publish Now Button Handler (Live Test)
async function triggerPublishNow() {
    if (isPublishing) return;
    isPublishing = true;

    const btn = document.getElementById('btn-publish-now');
    const progressBox = document.getElementById('publish-progress-box');
    const statusText = document.getElementById('progress-status-text');
    const barFill = document.getElementById('progress-bar-fill');
    const alertBox = document.getElementById('result-alert-box');

    btn.disabled = true;
    alertBox.style.display = 'none';
    progressBox.style.display = 'block';

    // Step progression animation
    const updateStep = (stepNum, text, percent) => {
        statusText.textContent = text;
        barFill.style.width = percent + '%';
        document.querySelectorAll('.progress-steps .step').forEach((s, idx) => {
            if (idx < stepNum) {
                s.className = 'step active';
            } else {
                s.className = 'step';
            }
        });
    };

    updateStep(1, 'جاري فحص الخلاصات واكتشاف أحدث خبر تقني...', 20);

    const stepTimer = setTimeout(() => {
        updateStep(2, 'جاري صياغة منشور لينكد إن المعماري وتحليل الأبعاد الهندسية...', 45);
    }, 4000);

    const stepTimer2 = setTimeout(() => {
        updateStep(3, 'جاري توليد تصميم إنفوجرافيك عالي الدقة عبر Nano Banana Pro...', 75);
    }, 12000);

    try {
        const response = await fetch('/api/publish-now', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        clearTimeout(stepTimer);
        clearTimeout(stepTimer2);

        const result = await response.json();
        updateStep(4, 'اكتملت العملية بنجاح!', 100);

        setTimeout(() => {
            progressBox.style.display = 'none';
            btn.disabled = false;
            isPublishing = false;

            if (result.success) {
                const postUrl = result.linkedin && result.linkedin.public_url ? result.linkedin.public_url : 'https://www.linkedin.com/feed/';
                const lkMethod = result.linkedin && result.linkedin.method === 'official_api' ? 'Official API (Safe)' : 'Session';

                alertBox.className = 'result-alert-box success';
                alertBox.innerHTML = `
                    <div style="font-weight: 700; margin-bottom: 6px;">🎉 تم النشر بنجاح على LinkedIn وتيليجرام!</div>
                    <div style="font-size: 13px; margin-bottom: 8px;">📌 <strong>الخبر:</strong> ${result.article_title}</div>
                    <div style="font-size: 12px; margin-bottom: 12px;">🛡️ <strong>طريقة النشر:</strong> ${lkMethod} • تم حفظ السجل وتفادي التكرار.</div>
                    <a href="${postUrl}" target="_blank" class="btn btn-secondary" style="padding: 6px 16px; font-size: 12px; display: inline-flex;">
                        🔗 عرض المنشور المنشور الآن على LinkedIn
                    </a>
                `;
                alertBox.style.display = 'block';

                // Refresh history and queue
                refreshHistory();
                refreshQueue();
                pollSystemStatus();
            } else {
                alertBox.className = 'result-alert-box error';
                alertBox.innerHTML = `
                    <div style="font-weight: 700; margin-bottom: 4px;">⚠️ تنبيه أثناء النشر:</div>
                    <div style="font-size: 13px;">${result.error || (result.linkedin && result.linkedin.error) || 'تعذر استكمال النشر'}</div>
                `;
                alertBox.style.display = 'block';
            }
        }, 1200);

    } catch (err) {
        clearTimeout(stepTimer);
        clearTimeout(stepTimer2);
        progressBox.style.display = 'none';
        btn.disabled = false;
        isPublishing = false;

        alertBox.className = 'result-alert-box error';
        alertBox.innerHTML = `<div>❌ حدث خطأ في الاتصال بالخادم: ${err.message}</div>`;
        alertBox.style.display = 'block';
    }
}

// 2b. Publish Directly to Telegram
async function triggerPublishTelegram() {
    if (isPublishing) return;
    isPublishing = true;

    const btnLk = document.getElementById('btn-publish-now');
    const btnTg = document.getElementById('btn-publish-telegram');
    const progressBox = document.getElementById('publish-progress-box');
    const statusText = document.getElementById('progress-status-text');
    const barFill = document.getElementById('progress-bar-fill');
    const alertBox = document.getElementById('result-alert-box');

    if (btnLk) btnLk.disabled = true;
    if (btnTg) btnTg.disabled = true;
    alertBox.style.display = 'none';
    progressBox.style.display = 'block';

    const updateStep = (stepNum, text, percent) => {
        statusText.textContent = text;
        barFill.style.width = percent + '%';
        document.querySelectorAll('.progress-steps .step').forEach((s, idx) => {
            if (idx < stepNum) {
                s.className = 'step active';
            } else {
                s.className = 'step';
            }
        });
    };

    updateStep(1, 'جاري رصد أحدث خبر تقني / فنتك / بروب تك...', 25);

    const stepTimer = setTimeout(() => {
        updateStep(2, 'جاري صياغة ملخص تيليجرام التقني والتحليل...', 50);
    }, 4000);

    const stepTimer2 = setTimeout(() => {
        updateStep(3, 'جاري إنشاء إنفوجرافيك نانو بانانا برو مع شارة التوقيع...', 75);
    }, 12000);

    try {
        const response = await fetch('/api/publish-telegram', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        clearTimeout(stepTimer);
        clearTimeout(stepTimer2);

        const result = await response.json();
        updateStep(4, 'تم الإرسال إلى تيليجرام بنجاح!', 100);

        setTimeout(() => {
            progressBox.style.display = 'none';
            if (btnLk) btnLk.disabled = false;
            if (btnTg) btnTg.disabled = false;
            isPublishing = false;

            if (result.success) {
                alertBox.className = 'result-alert-box success';
                alertBox.innerHTML = `
                    <div style="font-weight: 700; margin-bottom: 6px;">✈️ تم النشر بنجاح على قناة تيليجرام!</div>
                    <div style="font-size: 13px; margin-bottom: 8px;">📌 <strong>الخبر:</strong> ${result.article_title}</div>
                    <div style="font-size: 12px;">✅ تم إرسال الإنفوجرافيك مع الشارة الشخصية والملخص التقني المعتمد.</div>
                `;
                alertBox.style.display = 'block';

                refreshHistory();
                refreshQueue();
                pollSystemStatus();
            } else {
                alertBox.className = 'result-alert-box error';
                alertBox.innerHTML = `
                    <div style="font-weight: 700; margin-bottom: 4px;">⚠️ تنبيه أثناء النشر على تيليجرام:</div>
                    <div style="font-size: 13px;">${result.error || 'تعذر إرسال البوست إلى تيليجرام'}</div>
                `;
                alertBox.style.display = 'block';
            }
        }, 1200);

    } catch (err) {
        clearTimeout(stepTimer);
        clearTimeout(stepTimer2);
        progressBox.style.display = 'none';
        if (btnLk) btnLk.disabled = false;
        if (btnTg) btnTg.disabled = false;
        isPublishing = false;

        alertBox.className = 'result-alert-box error';
        alertBox.innerHTML = `<div>❌ حدث خطأ في الاتصال بالخادم: ${err.message}</div>`;
        alertBox.style.display = 'block';
    }
}

// 3. Schedule Management
async function saveSchedule(times, enabled) {
    try {
        const resp = await fetch('/api/schedule', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ times: times, enabled: enabled })
        });
        const res = await resp.json();
        if (res.success) {
            pollSystemStatus();
        }
    } catch (e) {
        console.error('Failed to save schedule:', e);
    }
}

function renderTimeChips() {
    const container = document.getElementById('time-slots-container');
    if (!container) return;
    container.innerHTML = '';
    activeScheduleTimes.forEach(time => {
        const chip = document.createElement('div');
        chip.className = 'time-chip';
        chip.setAttribute('data-time', time);
        chip.innerHTML = `
            <span class="time-value">${time}</span>
            <button class="chip-remove" onclick="removeTimeSlot('${time}')">×</button>
        `;
        container.appendChild(chip);
    });
}

function addTimeSlot() {
    const input = document.getElementById('new-slot-input');
    const timeVal = input ? input.value.trim() : '';
    if (!timeVal) return;

    if (!activeScheduleTimes.includes(timeVal)) {
        activeScheduleTimes.push(timeVal);
        activeScheduleTimes.sort();
        renderTimeChips();
        const toggle = document.getElementById('scheduler-toggle');
        saveSchedule(activeScheduleTimes, toggle ? toggle.checked : true);
    }
}

function removeTimeSlot(time) {
    activeScheduleTimes = activeScheduleTimes.filter(t => t !== time);
    renderTimeChips();
    const toggle = document.getElementById('scheduler-toggle');
    saveSchedule(activeScheduleTimes, toggle ? toggle.checked : true);
}

function applyGrowthStrategy() {
    activeScheduleTimes = ['08:45', '13:15', '18:45'];
    renderTimeChips();
    const toggle = document.getElementById('scheduler-toggle');
    saveSchedule(activeScheduleTimes, toggle ? toggle.checked : true);
}

function toggleScheduler(checkbox) {
    saveSchedule(activeScheduleTimes, checkbox.checked);
}

// 4. Save LinkedIn Token
async function saveLinkedInToken() {
    const input = document.getElementById('linkedin-token-input');
    const token = input ? input.value.trim() : '';
    if (!token) {
        alert('يرجى إدخال الـ Access Token');
        return;
    }

    try {
        const resp = await fetch('/api/save-linkedin-token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ access_token: token })
        });
        const res = await resp.json();
        if (res.success) {
            alert('✓ تم التحقق من حساب LinkedIn وحفظ الرمز بنجاح!');
            input.value = '';
            pollSystemStatus();
        } else {
            alert('⚠️ فشل التحقق من الرمز: ' + (res.error || 'رمز غير صالح'));
        }
    } catch (e) {
        alert('حدث خطأ أثناء حفظ الرمز: ' + e.message);
    }
}

// 5. Dynamic Queue and History Refresh
async function refreshQueue() {
    try {
        const resp = await fetch('/api/queue');
        const data = await resp.json();
        const list = document.getElementById('news-queue-list');
        if (!list) return;

        if (!data.articles || data.articles.length === 0) {
            list.innerHTML = '<div class="empty-state">لا توجد مقالات غير مقروءة حالياً.</div>';
            return;
        }

        list.innerHTML = data.articles.slice(0, 5).map(item => `
            <div class="queue-item">
                <div class="queue-meta">
                    <span class="queue-source">${item.source}</span>
                    <span class="queue-score">🎯 نقاط الأهمية: ${item.score}</span>
                </div>
                <h4 class="queue-title">${item.title}</h4>
            </div>
        `).join('');
    } catch (e) {
        console.warn('Queue refresh failed:', e);
    }
}

async function refreshHistory() {
    try {
        const resp = await fetch('/api/history');
        const data = await resp.json();
        const list = document.getElementById('history-list');
        if (!list) return;

        if (!data.history || data.history.length === 0) {
            list.innerHTML = '<div class="empty-state">لم يتم تسجيل منشورات سابقة بعد.</div>';
            return;
        }

        list.innerHTML = data.history.slice(0, 6).map(post => `
            <div class="history-item">
                <div class="history-badge">تم النشر ✓</div>
                <div class="history-content">
                    <h4 class="history-title">${post.title}</h4>
                    <span class="history-date">📅 ${post.published_at}</span>
                </div>
            </div>
        `).join('');
    } catch (e) {
        console.warn('History refresh failed:', e);
    }
}
