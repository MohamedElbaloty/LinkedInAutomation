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

    const step3Elem = document.getElementById('step-3');
    const step4Elem = document.getElementById('step-4');
    if (step3Elem) step3Elem.textContent = '3. تصميم بطاقة الخبر';
    if (step4Elem) step4Elem.textContent = '4. النشر على LinkedIn';

    updateStep(1, 'جاري فحص الخلاصات واكتشاف أحدث خبر تقني...', 20);

    const stepTimer = setTimeout(() => {
        updateStep(2, 'جاري صياغة منشور لينكد إن المعماري وتحليل الأبعاد الهندسية...', 45);
    }, 4000);

    const stepTimer2 = setTimeout(() => {
        updateStep(3, 'جاري تصميم بطاقة الخبر الصحفية فائقة الدقة...', 75);
    }, 10000);

    const stepTimer3 = setTimeout(() => {
        updateStep(4, 'جاري النشر على LinkedIn وتيليجرام...', 90);
    }, 18000);

    try {
        const response = await fetch('/api/publish-now', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        clearTimeout(stepTimer);
        clearTimeout(stepTimer2);
        clearTimeout(stepTimer3);

        const result = await response.json();
        updateStep(4, 'اكتمل النشر على LinkedIn وتيليجرام بنجاح!', 100);

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

    const step3Elem = document.getElementById('step-3');
    const step4Elem = document.getElementById('step-4');
    if (step3Elem) step3Elem.textContent = '3. تصميم بطاقة الخبر';
    if (step4Elem) step4Elem.textContent = '4. النشر على تيليجرام';

    updateStep(1, 'جاري رصد أحدث خبر تقني / فنتك / بروب تك...', 25);

    const stepTimer = setTimeout(() => {
        updateStep(2, 'جاري صياغة ملخص تيليجرام المعماري والتحليل...', 50);
    }, 4000);

    const stepTimer2 = setTimeout(() => {
        updateStep(3, 'جاري تصميم بطاقة الخبر الصحفية مع شارة التوقيع...', 75);
    }, 10000);

    const stepTimer3 = setTimeout(() => {
        updateStep(4, 'جاري النشر على قناة تيليجرام...', 90);
    }, 18000);

    try {
        const response = await fetch('/api/publish-telegram', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        clearTimeout(stepTimer);
        clearTimeout(stepTimer2);
        clearTimeout(stepTimer3);

        const result = await response.json();
        updateStep(4, 'تم النشر على تيليجرام بنجاح!', 100);

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

/* ==========================================================================
   LinkedIn Organic Commenting Engine Client Controller
   ========================================================================== */
let currentDraftPost = null;
let isDraftingComment = false;
let isPublishingComment = false;

async function triggerDraftComment() {
    if (isDraftingComment) return;
    isDraftingComment = true;

    const urlInput = document.getElementById('target-post-url-input');
    const draftBtn = document.getElementById('btn-draft-comment');
    const loadingBox = document.getElementById('comment-loading-box');
    const reviewBox = document.getElementById('comment-review-box');
    const alertBox = document.getElementById('comment-alert-box');

    const targetUrl = urlInput ? urlInput.value.trim() : '';

    draftBtn.disabled = true;
    alertBox.style.display = 'none';
    reviewBox.style.display = 'none';
    loadingBox.style.display = 'flex';

    try {
        const response = await fetch('/api/comment/draft', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target_url: targetUrl })
        });

        const data = await response.json();
        loadingBox.style.display = 'none';
        draftBtn.disabled = false;
        isDraftingComment = false;

        if (data.success) {
            currentDraftPost = data;

            document.getElementById('review-target-title').textContent = data.post_title || 'منشور قطاعي متخصص';
            document.getElementById('review-target-urn').textContent = data.post_urn || 'LinkedIn Feed Post';
            
            const linkElem = document.getElementById('review-target-url-link');
            if (linkElem) {
                linkElem.href = data.post_url || '#';
                linkElem.style.display = data.post_url ? 'inline-flex' : 'none';
            }

            const textarea = document.getElementById('review-comment-textarea');
            if (textarea) {
                textarea.value = data.comment_text || '';
            }

            reviewBox.style.display = 'block';
            reviewBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        } else {
            alertBox.className = 'comment-alert-box error';
            alertBox.innerHTML = `<strong>⚠️ تنبيه:</strong> ${data.error || 'تعذر استكشاف المنشور أو توليد التعليق.'}`;
            alertBox.style.display = 'block';
        }
    } catch (err) {
        loadingBox.style.display = 'none';
        draftBtn.disabled = false;
        isDraftingComment = false;
        alertBox.className = 'comment-alert-box error';
        alertBox.innerHTML = `<strong>❌ خطأ في الاتصال:</strong> ${err.message}`;
        alertBox.style.display = 'block';
    }
}

async function triggerPublishComment() {
    if (isPublishingComment || !currentDraftPost) return;
    isPublishingComment = true;

    const publishBtn = document.getElementById('btn-publish-comment');
    const textarea = document.getElementById('review-comment-textarea');
    const alertBox = document.getElementById('comment-alert-box');

    const commentText = textarea ? textarea.value.trim() : '';
    if (!commentText) {
        alert('الرجاء التأكد من وجود نص للتعليق قبل النشر.');
        isPublishingComment = false;
        return;
    }

    publishBtn.disabled = true;
    publishBtn.innerHTML = '<span class="spinner" style="width:16px;height:16px;border-width:2px;"></span> جاري النشر على LinkedIn...';
    alertBox.style.display = 'none';

    try {
        const response = await fetch('/api/comment/publish', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                target_urn: currentDraftPost.post_urn || currentDraftPost.post_url,
                comment_text: commentText,
                post_title: currentDraftPost.post_title
            })
        });

        const result = await response.json();
        publishBtn.disabled = false;
        publishBtn.innerHTML = '<span class="btn-icon">💬</span><span class="btn-text">علق الآن على LinkedIn</span>';
        isPublishingComment = false;

        if (result.success) {
            const viewUrl = result.public_url || (currentDraftPost.post_url ? currentDraftPost.post_url : 'https://www.linkedin.com/feed/');
            alertBox.className = 'comment-alert-box success';
            alertBox.innerHTML = `
                <div style="font-weight: 700; margin-bottom: 6px;">🎉 تم نشر تعليقك بنجاح وبشكل فوري على LinkedIn!</div>
                <div style="font-size: 13px; margin-bottom: 12px;">👤 المنشور المستهدف: <strong>${currentDraftPost.post_title}</strong></div>
                <a href="${viewUrl}" target="_blank" class="btn btn-secondary" style="padding: 8px 18px; font-size: 13px; display: inline-flex; align-items: center; gap: 6px;">
                    🔗 اضغط هنا لفتح المنشور على LinkedIn ومشاهدة تعليقك منشوراً الآن ↗️
                </a>
            `;
            alertBox.style.display = 'block';
            alertBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        } else {
            alertBox.className = 'comment-alert-box error';
            alertBox.innerHTML = `
                <div style="font-weight: 700; margin-bottom: 4px;">⚠️ تنبيه أثناء نشر التعليق:</div>
                <div style="font-size: 13px;">${result.error || 'تعذر إرسال التعليق إلى واجهة LinkedIn الرسمية. تأكد من ربط حسابك بـ Access Token.'}</div>
            `;
            alertBox.style.display = 'block';
        }
    } catch (err) {
        publishBtn.disabled = false;
        publishBtn.innerHTML = '<span class="btn-icon">💬</span><span class="btn-text">علق الآن على LinkedIn</span>';
        isPublishingComment = false;
        alertBox.className = 'comment-alert-box error';
        alertBox.innerHTML = `<strong>❌ خطأ غير متوقع:</strong> ${err.message}`;
        alertBox.style.display = 'block';
    }
}

async function toggleAutoComment(checkbox) {
    const isEnabled = checkbox.checked;
    const statusText = document.getElementById('auto-comment-status-text');

    if (statusText) {
        statusText.textContent = isEnabled ? 'التعليق الآلي: نشط 🟢' : 'التعليق الآلي: بانتظار تأكيدك ⚪';
        statusText.className = isEnabled ? 'auto-status-indicator active' : 'auto-status-indicator';
    }

    try {
        const resp = await fetch('/api/comment/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: isEnabled })
        });
        const data = await resp.json();
        console.log('Autonomous comment toggle result:', data);
    } catch (e) {
        console.error('Failed to toggle commenting mode:', e);
        checkbox.checked = !isEnabled;
    }
}
