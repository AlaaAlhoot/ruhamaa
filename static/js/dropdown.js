/**
 * dropdown.js — مكتبة القوائم المنسدلة للدول والمفاتيح
 * يُضمَّن بعد validation.js
 */

'use strict';

// ============================================================
// الحالة العامة
// ============================================================

let allCountries = [];   // كل الدول من API
let _ddInited    = false; // تم التهيئة؟

// ============================================================
// إعداد كل قائمة (config)
// key  => { type, hiddenIds, flagId, textId, dialId, errId }
// type: 'nat' | 'phone' | 'country'
// ============================================================

const DD_CONFIG = {
    nat: {
        type:      'nat',
        hiddenIds: ['nationality', 'nationality_code'],
        flagId:    'nat_flag',
        textId:    'nat_text',
        errId:     'err_nationality',
    },
    p1: {
        type:      'phone',
        hiddenIds: ['phone1_country'],
        flagId:    'p1_flag',
        dialId:    'p1_dial',
    },
    p2: {
        type:      'phone',
        hiddenIds: ['phone2_country'],
        flagId:    'p2_flag',
        dialId:    'p2_dial',
    },
    wa: {
        type:      'phone',
        hiddenIds: ['whatsapp_country'],
        flagId:    'wa_flag',
        dialId:    'wa_dial',
    },
    country: {
        type:      'country',
        hiddenIds: ['sponsor_country'],
        flagId:    'country_flag',
        textId:    'country_text',
        errId:     'err_sponsor_country',
    },

    // ── حقول البروفايل ──
    profile_phone: {
        type:      'phone',
        hiddenIds: ['fPhoneCountry'],
        flagId:    'profilePhoneFlag',
        dialId:    'profilePhoneDial',
    },
    profile_wa: {
        type:      'phone',
        hiddenIds: ['fWhatsappCountry'],
        flagId:    'profileWaFlag',
        dialId:    'profileWaDial',
    },
    profile_nationality: {
    type:      'nat',
    hiddenIds: ['fNationality', 'fNationalityCode'],
    flagId:    'profileNatFlag',
    textId:    'profileNatText',
    },
    profile_country: {
        type:      'country',
        hiddenIds: ['fCountry'],
        flagId:    'profileCountryFlag',
        textId:    'profileCountryText',
},
};

// ============================================================
// تحميل الدول
// ============================================================

/**
 * يجلب الدول من API ويخزنها في sessionStorage
 * فلسطين دائماً في الأعلى
 */
async function loadCountries() {
    // محاولة sessionStorage أولاً
    try {
        const cached = sessionStorage.getItem('ruhamaa_countries');
        if (cached) {
            allCountries = JSON.parse(cached);
            _initAllDropdowns();
            return;
        }
    } catch { /* تجاهل */ }

    try {
        const r    = await fetch('/api/countries/');
        const data = await r.json();
        let list   = data.countries || [];

        // فلسطين في الأعلى دائماً
        const ps  = list.find(c => c.code === 'PS');
        const rest = list.filter(c => c.code !== 'PS')
                         .sort((a, b) => (a.name_ar || '').localeCompare(b.name_ar || '', 'ar'));
        allCountries = ps ? [ps, ...rest] : rest;

        // تخزين في sessionStorage
        try {
            sessionStorage.setItem('ruhamaa_countries', JSON.stringify(allCountries));
        } catch { /* تجاهل في حال امتلأ */ }

        _initAllDropdowns();
    } catch (e) {
        console.error('loadCountries error:', e);
    }
}

function _initAllDropdowns() {
    if (_ddInited) return;
    _ddInited = true;

    // رسم كل القوائم
    Object.keys(DD_CONFIG).forEach(key => ddRender(key, allCountries));

    // تعيين فلسطين افتراضياً لكل القوائم
    const ps = allCountries.find(c => c.code === 'PS');
    if (ps) {
        ['nat', 'p1', 'p2', 'wa'].forEach(key => ddSelect(key, ps, false));
    }

    // إغلاق عند الضغط خارج القائمة
    document.addEventListener('click', _handleOutsideClick);

    // إغلاق بـ Escape
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') _closeAll();
    });
}

// ============================================================
// رسم القائمة
// ============================================================

/**
 * رسم عناصر القائمة
 * @param {string} key   - مفتاح DD_CONFIG
 * @param {Array}  list  - قائمة الدول المفلترة
 */
function ddRender(key, list) {
    const listEl = document.getElementById(`${key}_list`);
    if (!listEl) return;

    const cfg   = DD_CONFIG[key];
    const slice = list.slice(0, 80); // أقصى 80 نتيجة

    listEl.innerHTML = slice.map(c => {
        const name = c.name_ar || c.name_en || '';
        const flag = c.flag || '🌍';
        const dial = c.dial || '';
        // encode لمنع XSS في onclick
        const encoded = encodeURIComponent(JSON.stringify(c));

        return `
            <div class="dd-item" role="option"
                 onclick="ddSelectEncoded('${key}','${encoded}')"
                 tabindex="0"
                 onkeydown="if(event.key==='Enter'){ddSelectEncoded('${key}','${encoded}')}">
                <span class="dd-item-flag">${flag}</span>
                <span class="dd-item-name">${_escapeHtml(name)}</span>
                ${cfg.type !== 'country'
                    ? `<span class="dd-item-sub">${_escapeHtml(dial)}</span>`
                    : ''}
            </div>`;
    }).join('');
}

// wrapper آمن يفك الـ encoding
function ddSelectEncoded(key, encoded) {
    try {
        const c = JSON.parse(decodeURIComponent(encoded));
        ddSelect(key, c);
    } catch { /* تجاهل */ }
}

// ============================================================
// اختيار دولة
// ============================================================

/**
 * @param {string}  key        - مفتاح DD_CONFIG
 * @param {Object}  c          - بيانات الدولة
 * @param {boolean} [close=true] - إغلاق القائمة بعد الاختيار
 */
function ddSelect(key, c, close = true) {
    const cfg  = DD_CONFIG[key];
    const name = c.name_ar || c.name_en || '';
    const flag = c.flag || '🌍';
    const dial = c.dial || '+970';
    const code = c.code || '';

    if (cfg.type === 'nat') {
        _setEl(cfg.flagId, 'text', flag);
        _setEl(cfg.textId, 'text', name);
        _setHidden('nationality',      name);
        _setHidden('nationality_code', code);
        // مسح الخطأ
        if (cfg.errId) clearErr(null, cfg.errId);

    } else if (cfg.type === 'phone') {
        _setEl(cfg.flagId, 'text', flag);
        _setEl(cfg.dialId, 'text', dial);
        _setHidden(cfg.hiddenIds[0], dial);

        // تحديث placeholder حقل الرقم
        _updatePhonePlaceholder(key, dial);

        // تحديث maxlength حسب قاعدة الدولة
        _updatePhoneMaxlength(key, dial);

    } else if (cfg.type === 'country') {
        _setEl(cfg.flagId, 'text', flag);
        _setEl(cfg.textId, 'text', name);
        _setHidden(cfg.hiddenIds[0], name);
        if (cfg.errId) clearErr(null, cfg.errId);
    }

    // تحديد العنصر المحدد بصرياً
    const listEl = document.getElementById(`${key}_list`);
    listEl?.querySelectorAll('.dd-item').forEach(el => {
        el.classList.toggle('selected', el.querySelector('.dd-item-name')?.textContent === name);
    });

    if (close) ddClose(key);
}

function _updatePhonePlaceholder(key, dial) {
    // تعيين placeholder مناسب
    const phoneInputMap = { p1: 'phone1', p2: 'phone2', wa: 'whatsapp' };
    const inputId = phoneInputMap[key];
    if (!inputId) return;

    const inp = document.getElementById(inputId);
    if (!inp) return;

    const rule = PHONE_RULES?.[dial];
    if (rule?.digits) {
        // بناء مثال بصري
        inp.placeholder = '0'.repeat(rule.digits);
    } else {
        inp.placeholder = '05XXXXXXXX';
    }
}

function _updatePhoneMaxlength(key, dial) {
    const phoneInputMap = { p1: 'phone1', p2: 'phone2', wa: 'whatsapp' };
    const inputId = phoneInputMap[key];
    if (!inputId) return;

    const inp = document.getElementById(inputId);
    if (!inp) return;

    const rule = PHONE_RULES?.[dial];
    if (rule?.digits) {
        inp.setAttribute('maxlength', rule.digits);
    } else {
        inp.setAttribute('maxlength', rule?.max || 15);
    }
}

// ============================================================
// فتح / إغلاق / فلترة
// ============================================================

function ddToggle(key) {
    const dd  = document.getElementById(`${key}_dd`);
    const sel = document.getElementById(`${key}_sel`);
    if (!dd || !sel) return;

    const isOpen = dd.classList.contains('show');
    _closeAll();

    if (!isOpen) {
        dd.classList.add('show');
        sel.classList.add('open');
        sel.setAttribute('aria-expanded', 'true');
        ddRender(key, allCountries);
        // تركيز مربع البحث
        setTimeout(() => document.getElementById(`${key}_q`)?.focus(), 40);
    }
}

function ddClose(key) {
    const dd  = document.getElementById(`${key}_dd`);
    const sel = document.getElementById(`${key}_sel`);
    dd?.classList.remove('show');
    sel?.classList.remove('open');
    sel?.setAttribute('aria-expanded', 'false');
}

function _closeAll() {
    Object.keys(DD_CONFIG).forEach(k => ddClose(k));
}

function ddFilter(key, q) {
    const qLower = q.toLowerCase().trim();
    const filtered = qLower
        ? allCountries.filter(c =>
            (c.name_ar  || '').includes(q)                      ||
            (c.name_en  || '').toLowerCase().includes(qLower)   ||
            (c.dial     || '').includes(q)                      ||
            (c.code     || '').toLowerCase().includes(qLower)
          )
        : allCountries;
    ddRender(key, filtered);
}

function _handleOutsideClick(e) {
    Object.keys(DD_CONFIG).forEach(key => {
        // ابحث عن الـ wrapper
        const wrap = document.getElementById(`${key}_wrap`)
            || document.getElementById(`${key}_sel`)?.closest('.dd-wrap');
        if (wrap && !wrap.contains(e.target)) ddClose(key);
    });
}

// ============================================================
// مساعدات داخلية
// ============================================================

function _setEl(id, prop, val) {
    const el = document.getElementById(id);
    if (!el) return;
    if (prop === 'text') el.textContent = val;
    else el[prop] = val;
}

function _setHidden(id, val) {
    const el = document.getElementById(id);
    if (el) el.value = val;
}

function _escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// ============================================================
// دالة مساعدة لجلب مفتاح الدولة الحالي لحقل معين
// تُستخدم من validation.js
// ============================================================

function getDialCode(key) {
    return document.getElementById(DD_CONFIG[key]?.hiddenIds?.[0])?.value || '+970';
}
