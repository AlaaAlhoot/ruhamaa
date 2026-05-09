// ==================== Counter Animation ====================
function animateCounters() {
    document.querySelectorAll('.counter').forEach(el => {
        const target   = parseInt(el.dataset.target) || 0;
        const duration = 1500;
        const step     = target / (duration / 16);
        let current    = 0;

        const timer = setInterval(() => {
            current += step;
            if (current >= target) {
                el.textContent = target.toLocaleString('ar');
                clearInterval(timer);
            } else {
                el.textContent = Math.floor(current).toLocaleString('ar');
            }
        }, 16);
    });
}

// تشغيل عند الدخول للعنصر
const statsSection = document.querySelector('.stats-section');
if (statsSection) {
    const statsObserver = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounters();
                statsObserver.disconnect();
            }
        });
    }, { threshold: 0.3 });

    statsObserver.observe(statsSection);
}


// ==================== تواصل معنا ====================
function submitContact() {
    const name    = document.getElementById('contactName').value.trim();
    const email   = document.getElementById('contactEmail').value.trim();
    const phone   = document.getElementById('contactPhone').value.trim();
    const country = document.getElementById('contactCountry').value;
    const subject = document.getElementById('contactSubject').value.trim();
    const message = document.getElementById('contactMessage').value.trim();

    clearContactErrors();

    let valid = true;

    if (!name)    { showError('errName', 'الاسم مطلوب');               shakeField('contactName');    valid = false; }
    if (!email)   { showError('errEmail', 'البريد الإلكتروني مطلوب'); shakeField('contactEmail');   valid = false; }
    if (!phone)   { showError('errPhone', 'رقم الجوال مطلوب');        shakeField('contactPhone');   valid = false; }
    if (!subject) { showError('errSubject', 'عنوان الرسالة مطلوب');   shakeField('contactSubject'); valid = false; }
    if (!message) { showError('errMessage', 'الرسالة مطلوبة');        shakeField('contactMessage'); valid = false; }

    if (!valid) return;

    const fd = new FormData();
    fd.append('csrfmiddlewaretoken', getCookie('csrftoken'));
    fd.append('name',    name);
    fd.append('email',   email);
    fd.append('phone',   country + phone);
    fd.append('subject', subject);
    fd.append('message', message);

    const btn = document.getElementById('contactBtn');
    btn.disabled = true;

    fetch('/contact/', { method: 'POST', body: fd })
        .then(r => r.json())
        .then(data => {
            const alertEl = document.getElementById('contactAlert');
            if (data.status === 'success') {
                alertEl.innerHTML = `<div class="alert alert-success">${data.message}</div>`;
                ['contactName','contactEmail','contactPhone','contactSubject','contactMessage']
                    .forEach(id => document.getElementById(id).value = '');
            } else {
                if (data.errors) {
                    Object.entries(data.errors).forEach(([k, v]) => {
                        showError(`err${capitalize(k)}`, v);
                    });
                }
            }
            btn.disabled = false;
            setTimeout(() => alertEl.innerHTML = '', 4000);
        });
}

function clearContactErrors() {
    ['errName','errEmail','errPhone','errSubject','errMessage'].forEach(id => {
        const el = document.getElementById(id);
        if (el) { el.textContent = ''; el.style.display = 'none'; }
    });
}


// ==================== Helpers ====================
function showError(id, msg) {
    const el = document.getElementById(id);
    if (el) { el.textContent = msg; el.style.display = 'block'; }
}

function shakeField(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove('shake');
    void el.offsetWidth;
    el.classList.add('shake');
    el.addEventListener('animationend', () => el.classList.remove('shake'), { once: true });
}

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
}

function capitalize(str) {
    return str.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join('');
}