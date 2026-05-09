/**
 * validation.js — مكتبة التحقق المشتركة لمنصة رُحَمَاء
 * يُضمَّن في register.html قبل أي سكريبت آخر
 */

'use strict';

// ============================================================
// ثوابت
// ============================================================

const TODAY = (() => {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
})();

// قواعد الجوال حسب مفتاح الدولة (dial)
// digits = عدد الأرقام بعد المفتاح، prefix = البادئة المتوقعة (اختياري)
const PHONE_RULES = {
    '+970': { digits: 9, prefix: [] },
    '+972': { digits: 9, prefix: [] },
    '+20':  { digits: 11, prefix: ['01'] },
    '+962': { digits: 9,  prefix: ['07'] },
    '+966': { digits: 9,  prefix: ['05'] },
    '+971': { digits: 9,  prefix: ['05','056','052','050','055','054','058'] },
    '+965': { digits: 8,  prefix: [] },
    '+973': { digits: 8,  prefix: [] },
    '+974': { digits: 8,  prefix: [] },
    '+218': { digits: 9,  prefix: ['09','02'] },
    '+212': { digits: 9,  prefix: ['06','07'] },
    '+216': { digits: 8,  prefix: ['2','3','4','5','7','9'] },
    '+213': { digits: 9,  prefix: ['05','06','07'] },
    '+249': { digits: 9,  prefix: ['09','01'] },
    '+963': { digits: 9,  prefix: ['09'] },
    '+964': { digits: 10, prefix: ['07'] },
    '+90':  { digits: 10, prefix: ['05'] },
    '+49':  { digits: 10, prefix: [] },
    '+44':  { digits: 10, prefix: ['07'] },
    '+1':   { digits: 10, prefix: [] },
    '+33':  { digits: 9,  prefix: ['06','07'] },
    '+39':  { digits: 10, prefix: ['03'] },
    '+34':  { digits: 9,  prefix: ['06','07'] },
    '+31':  { digits: 9,  prefix: ['06'] },
    '+46':  { digits: 9,  prefix: ['07'] },
    '+47':  { digits: 8,  prefix: ['4','9'] },
    '+45':  { digits: 8,  prefix: [] },
    '+48':  { digits: 9,  prefix: ['5','6','7'] },
    '+7':   { digits: 10, prefix: ['9'] },
    '+81':  { digits: 10, prefix: ['07','08','09'] },
    '+86':  { digits: 11, prefix: ['1'] },
    '+91':  { digits: 10, prefix: ['6','7','8','9'] },
    '+55':  { digits: 11, prefix: ['9'] },
    '+27':  { digits: 9,  prefix: ['06','07','08'] },
    // default للدول غير المعروفة
    'default': { digits: null, min: 7, max: 15 },
};

// ============================================================
// 1. حالة الحقل البصرية (✅ / ❌ + حدود + رسالة)
// ============================================================

/**
 * ضبط حالة الحقل بصرياً
 * @param {string} inputId  - id العنصر
 * @param {boolean} valid   - true = صح، false = خطأ
 * @param {string} message  - الرسالة تحت الحقل
 * @param {string} [hintId] - id عنصر الرسالة (افتراضي: err_inputId)
 */
function setFieldState(inputId, valid, message = '', hintId = null) {
    const inp  = document.getElementById(inputId);
    const errId = hintId || `err_${inputId}`;
    const err  = document.getElementById(errId);

    if (!inp) return;

    // إزالة الأيقونة القديمة
    inp.parentElement?.querySelector('.field-icon')?.remove();

    if (valid) {
        inp.classList.remove('is-invalid');
        inp.classList.add('is-valid');

        // أيقونة ✓ داخل الحقل
        _appendIcon(inp, '✓', '#1a7a4a');

        if (err) {
            err.classList.remove('show');
            const span = err.querySelector('span:last-child');
            if (span) span.textContent = '';
        }

        // رسالة خضراء إذا وُجدت
        if (message) _showHint(inputId, message, true);

    } else {
        inp.classList.add('is-invalid');
        inp.classList.remove('is-valid');

        // أيقونة ✗ داخل الحقل
        _appendIcon(inp, '✗', '#e53e3e');

        if (err) {
            err.classList.add('show');
            const span = err.querySelector('span:last-child');
            if (span) span.textContent = message;
        }

        _showHint(inputId, message, false);
    }
}

function _appendIcon(inp, symbol, color) {
    // لا نضع الأيقونة على select أو file
    if (inp.tagName === 'SELECT' || inp.type === 'file') return;

    // تأكد أن الـ parent مُهيأ للـ absolute positioning
    const parent = inp.parentElement;
    if (!parent) return;
    if (getComputedStyle(parent).position === 'static') {
        parent.style.position = 'relative';
    }

    const icon = document.createElement('span');
    icon.className = 'field-icon';
    icon.textContent = symbol;
    icon.style.cssText = [
        'position:absolute',
        'top:50%',
        'left:10px',
        'transform:translateY(-50%)',
        `color:${color}`,
        'font-size:0.85rem',
        'font-weight:700',
        'pointer-events:none',
        'z-index:5',
        'line-height:1',
    ].join(';');

    parent.appendChild(icon);
}

function _showHint(inputId, message, ok) {
    // ابحث عن عنصر hint مخصص أسفل الحقل
    const hintEl = document.getElementById(`hint_${inputId}`);
    if (!hintEl) return;
    hintEl.innerHTML = ok
        ? `<span style="color:#1a7a4a">✅ ${message}</span>`
        : `<span style="color:#e53e3e">❌ ${message}</span>`;
}

// ============================================================
// 2. تنظيف المدخل
// ============================================================

/**
 * تنظيف النص من رموز XSS
 */
function sanitize(val) {
    return String(val)
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;')
        .trim();
}

// ============================================================
// 3. تحقق رقم الهوية
// ============================================================

/**
 * تحقق فوري من صيغة رقم الهوية
 * يبدأ بـ 9 أو 8 أو 4 أو 7 — 9 أرقام
 */
function validateIdFormat(value) {
    return /^[9847]\d{8}$/.test(value.trim());
}

/**
 * ربط حقل رقم الهوية بالتحقق الفوري مع API
 * @param {string} inputId   - id حقل الإدخال
 * @param {string} [errId]   - id رسالة الخطأ
 * @param {string} [hintId]  - id رسالة التلميح
 */
function bindIdField(inputId, errId, hintId) {
    const inp = document.getElementById(inputId);
    if (!inp) return;

    // تعيين max date لمنع أخطاء مستقبلية
    inp.setAttribute('maxlength', '9');
    inp.setAttribute('inputmode', 'numeric');

    let debTimer;
    inp.addEventListener('input', function () {
        const v = this.value.replace(/\D/g, '').slice(0, 9);
        this.value = v;

        clearTimeout(debTimer);
        if (!v) {
            clearFieldState(inputId, errId);
            return;
        }

        if (!validateIdFormat(v)) {
            setFieldState(inputId, false, 'رقم الهوية يجب 9 أرقام يبدأ بـ 9 أو 8 أو 4 أو 7', errId);
            return;
        }

        // صيغة صحيحة — تحقق من التكرار
        setFieldState(inputId, true, 'صيغة صحيحة... جار التحقق', errId);
        debTimer = setTimeout(async () => {
            await _checkUniqueAndSet(inputId, 'id_number', v, errId,
                'رقم الهوية مسجّل مسبقاً في النظام', 'رقم الهوية متاح ✅');
        }, 600);
    });

    inp.addEventListener('blur', function () {
        clearTimeout(debTimer);
        const v = this.value.trim();
        if (!v) { clearFieldState(inputId, errId); return; }
        if (!validateIdFormat(v)) {
            setFieldState(inputId, false, 'رقم الهوية يجب 9 أرقام يبدأ بـ 9 أو 8 أو 4 أو 7', errId);
        }
    });
}

// ============================================================
// 4. تحقق النص العربي
// ============================================================

/**
 * ربط حقل اسم عربي بالتحقق الفوري
 */
function bindArabicField(inputId, errId, label, allowEnglish = false) {
    const inp = document.getElementById(inputId);
    if (!inp) return;

    const pattern = allowEnglish
        ? /^[\u0600-\u06FFa-zA-Z]+$/
        : /^[\u0600-\u06FF]+$/;

    const errorMsg = allowEnglish
        ? `${label} يجب أن يحتوي على أحرف عربية أو إنجليزية فقط`
        : `${label} يجب أن يكون نصاً عربياً فقط`;

    const _validate = function () {
        // حذف الأرقام والرموز والمسافات مباشرة عند الإدخال
        this.value = this.value.replace(/[0-9\s<>"';&\/\\*@#$%^()+=\[\]{},.:!?|~`\-_]/g, '');

        const v = this.value.trim();
        if (!v) { clearFieldState(inputId, errId); return; }

        if (!pattern.test(v)) {
            setFieldState(inputId, false, errorMsg, errId);
        } else {
            setFieldState(inputId, true, '', errId);
        }
    };

    inp.addEventListener('input', _validate);
    inp.addEventListener('blur',  _validate);
}

// ============================================================
// 5. تحقق البريد الإلكتروني
// ============================================================

function bindEmailField(inputId, errId) {
    const inp = document.getElementById(inputId);
    if (!inp) return;

    let debTimer;
    inp.addEventListener('input', function () {
        // منع رموز XSS
        this.value = this.value.replace(/[<>"';]/g, '');
        clearTimeout(debTimer);
        const v = this.value.trim();
        if (!v) { clearFieldState(inputId, errId); return; }

        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) {
            setFieldState(inputId, false, 'البريد الإلكتروني غير صالح', errId);
            return;
        }

        setFieldState(inputId, true, 'جار التحقق...', errId);
        debTimer = setTimeout(async () => {
            await _checkUniqueAndSet(inputId, 'email', v, errId,
                'البريد الإلكتروني مستخدم مسبقاً', 'البريد الإلكتروني متاح ✅');
        }, 600);
    });

    inp.addEventListener('blur', function () {
        clearTimeout(debTimer);
        const v = this.value.trim();
        if (!v) { clearFieldState(inputId, errId); return; }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) {
            setFieldState(inputId, false, 'البريد الإلكتروني غير صالح', errId);
        }
    });
}

// ============================================================
// 6. تحقق اسم المستخدم
// ============================================================

function bindUsernameField(inputId, errId) {
    const inp = document.getElementById(inputId);
    if (!inp) return;

    let debTimer;
    inp.addEventListener('input', function () {
        // منع الحروف العربية والمسافات مباشرة عند الإدخال
        this.value = this.value.replace(/[\u0600-\u06FF\s]/g, '');

        clearTimeout(debTimer);
        const v = this.value.trim();
        if (!v) { clearFieldState(inputId, errId); return; }

        // منع الرموز الخطيرة
        if (/[<>'";&]/.test(v)) {
            setFieldState(inputId, false, 'اسم المستخدم يحتوي على رموز غير مسموح بها', errId);
            return;
        }

        if (v.length < 4) {
            setFieldState(inputId, false, 'اسم المستخدم يجب أن يكون 4 أحرف على الأقل', errId);
            return;
        }
        if (v.length > 50) {
            setFieldState(inputId, false, 'اسم المستخدم لا يتجاوز 50 حرفاً', errId);
            return;
        }

        setFieldState(inputId, true, 'جار التحقق...', errId);
        debTimer = setTimeout(async () => {
            await _checkUniqueAndSet(inputId, 'username', v, errId,
                'اسم المستخدم مستخدم مسبقاً', 'اسم المستخدم متاح ✅');
        }, 600);
    });
}

// ============================================================
// 7. تحقق رقم الجوال
// ============================================================

/**
 * التحقق من صيغة رقم الجوال حسب مفتاح الدولة
 * @param {string} phone - الرقم بدون مفتاح الدولة
 * @param {string} dial  - مفتاح الدولة مثل "+970"
 * @returns {{ valid: boolean, message: string }}
 */
function validatePhoneFormat(phone, dial) {
    const v = phone.trim();
    if (!v) return { valid: false, message: 'رقم الجوال مطلوب' };
    if (!/^\d+$/.test(v)) return { valid: false, message: 'أدخل أرقاماً فقط' };

    const rule = PHONE_RULES[dial] || PHONE_RULES['default'];

    if (rule.digits) {
        // قاعدة محددة
        if (v.length !== rule.digits) {
            return { valid: false, message: `رقم الجوال يجب أن يكون ${rule.digits} أرقام لهذه الدولة` };
        }
        if (rule.prefix && rule.prefix.length > 0) {
            const ok = rule.prefix.some(p => v.startsWith(p));
            if (!ok) {
                return { valid: false, message: `رقم الجوال يجب أن يبدأ بـ ${rule.prefix.slice(0,3).join(' أو ')}` };
            }
        }
    } else {
        // default
        if (v.length < rule.min || v.length > rule.max) {
            return { valid: false, message: `رقم الجوال يجب أن يكون بين ${rule.min} و${rule.max} رقماً` };
        }
    }

    return { valid: true, message: 'رقم صالح' };
}

/**
 * ربط حقل جوال بالتحقق الفوري
 * @param {string} inputId     - id حقل الجوال
 * @param {string} dialGetterFn - دالة تعيد مفتاح الدولة الحالي (string)
 * @param {string} errId
 * @param {string} hintId
 * @param {boolean} checkDb    - هل نتحقق من التكرار في قاعدة البيانات
 * @param {string} dbField     - اسم الحقل في API ('phone1'|'phone2'|'whatsapp')
 * @param {string} [phone1InputId] - id حقل الجوال الأول (للمقارنة في phone2)
 */
function bindPhoneField(inputId, dialGetterFn, errId, hintId, checkDb, dbField, phone1InputId) {
    const inp = document.getElementById(inputId);
    if (!inp) return;

    let debTimer;

    const _check = async () => {
        const v    = inp.value.trim();
        const dial = dialGetterFn();

        if (!v) { clearFieldState(inputId, errId); _clearHint(hintId); return; }

        // تحقق من الصيغة أولاً
        const fmt = validatePhoneFormat(v, dial);
        if (!fmt.valid) {
            setFieldState(inputId, false, fmt.message, errId);
            _clearHint(hintId);
            return;
        }

        // phone2: مقارنة مع phone1
        if (phone1InputId) {
            const p1 = document.getElementById(phone1InputId)?.value?.trim();
            if (p1 && v === p1) {
                setFieldState(inputId, false, 'رقم الجوال الثاني يجب أن يختلف عن الأول', errId);
                return;
            }
        }

        // صيغة صحيحة
        setFieldState(inputId, true, 'جار التحقق...', errId);

        if (checkDb) {
            const fd = new FormData();
            fd.append('csrfmiddlewaretoken', _getCSRF());
            fd.append('field', dbField);
            fd.append('value', v);
            if (dbField === 'phone2' && phone1InputId) {
                fd.append('phone1_value', document.getElementById(phone1InputId)?.value?.trim() || '');
            }

            try {
                const r    = await fetch('/api/check-unique/', { method: 'POST', body: fd });
                const data = await r.json();
                if (!data.unique) {
                    setFieldState(inputId, false, data.message, errId);
                } else {
                    setFieldState(inputId, true, 'رقم متاح ✅', errId);
                }
            } catch {
                setFieldState(inputId, true, fmt.message, errId);
            }
        } else {
            // واتساب — تحقق صيغة فقط
            setFieldState(inputId, true, fmt.message, errId);
        }
    };

    inp.addEventListener('input', function () {
        this.value = this.value.replace(/\D/g, '');
        clearTimeout(debTimer);
        debTimer = setTimeout(_check, 600);
    });

    inp.addEventListener('blur', () => {
    // لا تعيد التحقق إذا كان الحقل محسوماً بالفعل من debounce
    if (inp.classList.contains('is-valid') || inp.classList.contains('is-invalid')) return;
    _check();
});
}

function _clearHint(hintId) {
    const el = document.getElementById(hintId);
    if (el) el.innerHTML = '';
}

// ============================================================
// 8. تحقق تاريخ الميلاد
// ============================================================

/**
 * ربط حقل تاريخ الميلاد — يمنع التواريخ المستقبلية
 */
function bindDateField(inputId, errId) {
    const inp = document.getElementById(inputId);
    if (!inp) return;

    // تعيين الحد الأقصى = اليوم
    inp.setAttribute('max', TODAY);

    inp.addEventListener('change', function () {
        const v = this.value;
        if (!v) { clearFieldState(inputId, errId); return; }
        if (v > TODAY) {
            setFieldState(inputId, false, 'تاريخ الميلاد لا يمكن أن يكون في المستقبل', errId);
            this.value = '';
        } else {
            setFieldState(inputId, true, '', errId);
        }
    });
}

// ============================================================
// 9. تحقق الرقم الموجب
// ============================================================

function bindNumberField(inputId, errId, label, min = 0) {
    const inp = document.getElementById(inputId);
    if (!inp) return;

    inp.setAttribute('min', min);

    inp.addEventListener('input', function () {
        const v = parseFloat(this.value);
        if (isNaN(v) || v < min) {
            setFieldState(inputId, false, `${label} يجب أن يكون ${min} على الأقل`, errId);
        } else {
            setFieldState(inputId, true, '', errId);
        }
    });
}

// ============================================================
// 10. تحقق من التكرار عبر API (داخلي)
// ============================================================

async function _checkUniqueAndSet(inputId, field, value, errId, errMsg, okMsg) {
    const fd = new FormData();
    fd.append('csrfmiddlewaretoken', _getCSRF());
    fd.append('field', field);
    fd.append('value', value);

    try {
        const r    = await fetch('/api/check-unique/', { method: 'POST', body: fd });
        const data = await r.json();
        if (!data.unique) {
            setFieldState(inputId, false, data.message || errMsg, errId);
            return false;
        }
        setFieldState(inputId, true, okMsg, errId);
        return true;
    } catch {
        // فشل الـ API — نكمل
        return true;
    }
}

/**
 * دالة عامة للاستخدام خارجياً (step2Next, step3Next)
 */
async function checkUnique(field, value, inputId, errId) {
    if (!value) return true;
    return _checkUniqueAndSet(inputId, field, value, errId,
        'هذه القيمة مستخدمة مسبقاً', 'متاح ✅');
}

// ============================================================
// 11. مساعدات عامة
// ============================================================

function clearFieldState(inputId, errId) {
    const inp = document.getElementById(inputId);
    if (inp) {
        inp.classList.remove('is-valid', 'is-invalid');
        inp.parentElement?.querySelector('.field-icon')?.remove();
    }
    const err = document.getElementById(errId);
    if (err) {
        err.classList.remove('show');
        const span = err.querySelector('span:last-child');
        if (span) span.textContent = '';
    }
}

function _getCSRF() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value
        || document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='))?.split('=')[1]
        || '';
}

/** قيمة حقل */
function gv(id) {
    return document.getElementById(id)?.value?.trim() || '';
}

/** إظهار خطأ + shake */
function fErr(inputId, errId, msg) {
    setFieldState(inputId, false, msg, errId);
    shakeEl(inputId);
}

/** إزالة خطأ */
function clearErr(inputId, errId) {
    clearFieldState(inputId, errId);
}

function showErr(errId) {
    document.getElementById(errId)?.classList.add('show');
}

function shakeEl(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove('shake');
    void el.offsetWidth;
    el.classList.add('shake');
    el.addEventListener('animationend', () => el.classList.remove('shake'), { once: true });
}

function scrollToField(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setTimeout(() => el.focus?.(), 400);
}

function showAlert(type, msg) {
    const el = document.getElementById('regAlert');
    if (!el) return;
    el.className = `reg-alert show ${type}`;
    el.innerHTML = (type === 'success' ? '✅ ' : '⚠️ ') + msg;
    if (type !== 'success') setTimeout(() => el.classList.remove('show'), 6000);
}

function togglePass(id) {
    const el = document.getElementById(id);
    if (el) el.type = el.type === 'password' ? 'text' : 'password';
}

// ============================================================
// 12. قوة كلمة المرور
// ============================================================

function checkPassStr() {
    const p    = gv('password');
    const bar  = document.getElementById('passBar');
    const hint = document.getElementById('passHint');
    if (!bar || !hint) return;

    let s = 0;
    if (p.length >= 8)          s++;
    if (/[A-Z]/.test(p))        s++;
    if (/\d/.test(p))           s++;
    if (/[^A-Za-z0-9]/.test(p)) s++;

    const lvls = [
        { w: '0%',   c: 'transparent', t: '' },
        { w: '25%',  c: '#e53e3e',     t: '🔴 ضعيفة' },
        { w: '50%',  c: '#ed8936',     t: '🟠 مقبولة' },
        { w: '75%',  c: '#ecc94b',     t: '🟡 جيدة'  },
        { w: '100%', c: '#1a7a4a',     t: '🟢 قوية'  },
    ];

    bar.style.width      = lvls[s].w;
    bar.style.background = lvls[s].c;
    hint.textContent     = lvls[s].t;
    hint.style.color     = lvls[s].c;
}

function checkPassMatch() {
    const p1   = gv('password');
    const p2   = gv('password2');
    const el   = document.getElementById('passMatch');
    const inp2 = document.getElementById('password2');
    if (!el || !inp2 || !p2) {
        if (el) el.textContent = '';
        return;
    }
    if (p1 === p2) {
        el.innerHTML = '<span style="color:#1a7a4a">✅ متطابقتان</span>';
        inp2.classList.add('is-valid');
        inp2.classList.remove('is-invalid');
    } else {
        el.innerHTML = '<span style="color:#e53e3e">❌ غير متطابقتين</span>';
        inp2.classList.add('is-invalid');
        inp2.classList.remove('is-valid');
    }
}

// ============================================================
// 13. تحقق رقم الهوية المباشر (liveId) — مشترك بين كل الملفات
// ============================================================

function liveId(inp, hintId) {
    const v = inp.value.replace(/\D/g, '').slice(0, 9);
    inp.value = v;
    const h = document.getElementById(hintId);
    if (!h) return;

    if (!v) {
        h.textContent = '';
        inp.classList.remove('is-valid', 'is-invalid');
        inp.parentElement?.querySelector('.field-icon')?.remove();
        return;
    }

    if (/^[9847]\d{8}$/.test(v)) {
        h.innerHTML = '<span style="color:#1a7a4a">✅ رقم هوية صالح</span>';
        inp.classList.add('is-valid');
        inp.classList.remove('is-invalid');
        _appendIcon(inp, '✓', '#1a7a4a');
    } else {
        h.innerHTML = '<span style="color:#e53e3e">❌ 9 أرقام تبدأ بـ 9 أو 8 أو 4 أو 7</span>';
        inp.classList.add('is-invalid');
        inp.classList.remove('is-valid');
        _appendIcon(inp, '✗', '#e53e3e');
    }
}

// ============================================================
// 14. Unsaved Changes Warning
// ============================================================

let _formDirty = false;

function markDirty() { _formDirty = true; }
function markClean()  { _formDirty = false; }

window.addEventListener('beforeunload', (e) => {
    if (_formDirty) {
        e.preventDefault();
        e.returnValue = 'هل تريد مغادرة الصفحة؟ البيانات غير المحفوظة ستُفقد.';
    }
});

// تفعيل dirty على أي تغيير في الصفحة
document.addEventListener('DOMContentLoaded', () => {
    document.addEventListener('input',  markDirty);
    document.addEventListener('change', markDirty);
});
// ── مسح الخطأ تلقائياً عند تغيير أي حقل ──
document.addEventListener('change', function (e) {
    const el = e.target;
    if (!el.id) return;

    if (el.value) {
        el.classList.remove('is-invalid');
        el.classList.add('is-valid');
        const errEl = document.getElementById('err_' + el.id);
        if (errEl) {
            errEl.classList.remove('show');
            const span = errEl.querySelector('span:last-child');
            if (span) span.textContent = '';
        }
    }
});
