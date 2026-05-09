const CSRF = getCookie('csrftoken');

// ==================== تسجيل الدخول ====================
function submitLogin() {
    const identifier = document.getElementById('identifier').value.trim();
    const password   = document.getElementById('password').value.trim();
    const alertEl    = document.getElementById('loginAlert');

    if (!identifier || !password) {
        alertEl.innerHTML = `<div class="alert alert-warning">يرجى تعبئة جميع الحقول</div>`;
        return;
    }

    const fd = new FormData();
    fd.append('csrfmiddlewaretoken', CSRF);
    fd.append('identifier', identifier);
    fd.append('password',   password);

    fetch('/login/', { method: 'POST', body: fd })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                window.location.href = data.redirect;
            } else {
                alertEl.innerHTML = `<div class="alert alert-danger">${data.message}</div>`;
                shakeField('identifier');
                shakeField('password');
            }
        });
}


// ==================== التسجيل ====================
// إظهار/إخفاء الحقول حسب النوع
document.querySelectorAll('input[name="userType"]').forEach(radio => {
    radio.addEventListener('change', function() {
        const isSponsor = this.value === 'sponsor';
        document.getElementById('usernameField').classList.toggle('d-none', !isSponsor);
        document.getElementById('idField').classList.toggle('d-none', isSponsor);
    });
});

function submitRegister() {
    const userType = document.querySelector('input[name="userType"]:checked');
    const alertEl  = document.getElementById('registerAlert');

    if (!userType) {
        alertEl.innerHTML = `<div class="alert alert-warning">يرجى اختيار نوع الحساب</div>`;
        return;
    }

    const password  = document.getElementById('regPassword').value;
    const password2 = document.getElementById('regPassword2').value;

    if (password !== password2) {
        showError('errPassword', 'كلمتا المرور غير متطابقتان');
        shakeField('regPassword2');
        return;
    }

    const fd = new FormData();
    fd.append('csrfmiddlewaretoken', CSRF);
    fd.append('user_type',   userType.value);
    fd.append('first_name',  document.getElementById('firstName').value.trim());
    fd.append('second_name', document.getElementById('secondName').value.trim());
    fd.append('third_name',  document.getElementById('thirdName').value.trim());
    fd.append('family_name', document.getElementById('familyName').value.trim());
    fd.append('email',       document.getElementById('regEmail').value.trim());
    fd.append('phone',       document.getElementById('regCountry').value + document.getElementById('regPhone').value.trim());
    fd.append('password',    password);

    if (userType.value === 'sponsor') {
        fd.append('username', document.getElementById('username').value.trim());
    } else {
        fd.append('id_number', document.getElementById('idNumber').value.trim());
    }

    fetch('/register/', { method: 'POST', body: fd })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                window.location.href = data.redirect;
            } else if (data.status === 'pending') {
                alertEl.innerHTML = `<div class="alert alert-success">${data.message}</div>`;
            } else {
                if (data.errors) {
                    Object.entries(data.errors).forEach(([k, v]) => {
                        const key = k.split('_').map((w,i) => i===0 ? w.charAt(0).toUpperCase()+w.slice(1) : w.charAt(0).toUpperCase()+w.slice(1)).join('');
                        showError(`err${key}`, v);
                        shakeField(k);
                    });
                }
            }
        });
}


// ==================== استرجاع كلمة المرور ====================
function sendOTP() {
    const email   = document.getElementById('otpEmail').value.trim();
    const alertEl = document.getElementById('otpAlert');

    if (!email) { alertEl.innerHTML = `<div class="alert alert-warning">أدخل بريدك الإلكتروني</div>`; return; }

    const fd = new FormData();
    fd.append('csrfmiddlewaretoken', CSRF);
    fd.append('step',  'send_otp');
    fd.append('email', email);

    fetch('/forgot-password/', { method: 'POST', body: fd })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                alertEl.innerHTML = `<div class="alert alert-success">${data.message}</div>`;
                document.getElementById('step1').classList.add('d-none');
                document.getElementById('step2').classList.remove('d-none');
            } else {
                alertEl.innerHTML = `<div class="alert alert-danger">${data.message}</div>`;
            }
        });
}

function verifyOTP() {
    const email   = document.getElementById('otpEmail').value.trim();
    const code    = document.getElementById('otpCode').value.trim();
    const alertEl = document.getElementById('otpAlert');

    const fd = new FormData();
    fd.append('csrfmiddlewaretoken', CSRF);
    fd.append('step',  'verify_otp');
    fd.append('email', email);
    fd.append('code',  code);

    fetch('/forgot-password/', { method: 'POST', body: fd })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                document.getElementById('step2').classList.add('d-none');
                document.getElementById('step3').classList.remove('d-none');
                alertEl.innerHTML = '';
            } else {
                alertEl.innerHTML = `<div class="alert alert-danger">${data.message}</div>`;
                shakeField('otpCode');
            }
        });
}

function resetPassword() {
    const email    = document.getElementById('otpEmail').value.trim();
    const password = document.getElementById('newPass').value;
    const password2= document.getElementById('newPass2').value;
    const alertEl  = document.getElementById('otpAlert');

    if (password !== password2) {
        showError('errNewPass', 'كلمتا المرور غير متطابقتان');
        shakeField('newPass2');
        return;
    }

    const fd = new FormData();
    fd.append('csrfmiddlewaretoken', CSRF);
    fd.append('step',     'reset_password');
    fd.append('email',    email);
    fd.append('password', password);

    fetch('/forgot-password/', { method: 'POST', body: fd })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                alertEl.innerHTML = `<div class="alert alert-success">${data.message}</div>`;
                setTimeout(() => window.location.href = '/login/', 2000);
            } else {
                alertEl.innerHTML = `<div class="alert alert-danger">${data.message}</div>`;
            }
        });
}


// ==================== Helpers ====================
function togglePass(id) {
    const el = document.getElementById(id);
    el.type = el.type === 'password' ? 'text' : 'password';
}

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