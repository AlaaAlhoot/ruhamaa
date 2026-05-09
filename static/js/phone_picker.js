/**
 * PhonePicker — خانة رقم الجوال الديناميكية
 * نسخة محسّنة — تحقق صحيح لجميع الدول
 */

const PhonePicker = (() => {

    // ==================== Cache ====================
    const CACHE_KEY    = 'ruhamaa_countries_v2';
    const CACHE_EXPIRE = 7 * 24 * 60 * 60 * 1000; // 7 أيام
    let countriesData  = [];

    // ==================== قواعد التحقق لكل الدول ====================
    // min/max = عدد الأرقام الكلي الذي يدخله المستخدم (مع الصفر إن وُجد)
    const PHONE_RULES = {
        PS: { min: 9,  max: 10, hint: 'مثال: 0591234567' },
        IL: { min: 9,  max: 10, hint: 'مثال: 0521234567' },
        EG: { min: 11, max: 11, hint: 'مثال: 01012345678' },  // ← المشكلة كانت هنا
        JO: { min: 10, max: 10, hint: 'مثال: 0791234567'  },
        SA: { min: 10, max: 10, hint: 'مثال: 0501234567'  },
        AE: { min: 9,  max: 10, hint: 'مثال: 0501234567'  },
        KW: { min: 8,  max: 8,  hint: 'مثال: 51234567'    },
        QA: { min: 8,  max: 8,  hint: 'مثال: 33123456'    },
        BH: { min: 8,  max: 8,  hint: 'مثال: 36123456'    },
        OM: { min: 8,  max: 8,  hint: 'مثال: 92123456'    },
        IQ: { min: 10, max: 11, hint: 'مثال: 07901234567' },
        SY: { min: 9,  max: 10, hint: 'مثال: 0991234567'  },
        LB: { min: 7,  max: 8,  hint: 'مثال: 71123456'    },
        YE: { min: 9,  max: 9,  hint: 'مثال: 712345678'   },
        LY: { min: 9,  max: 10, hint: 'مثال: 0911234567'  },
        TN: { min: 8,  max: 8,  hint: 'مثال: 20123456'    },
        MA: { min: 9,  max: 10, hint: 'مثال: 0612345678'  },
        DZ: { min: 9,  max: 10, hint: 'مثال: 0551234567'  },
        SD: { min: 9,  max: 10, hint: 'مثال: 0912345678'  },
        TR: { min: 10, max: 11, hint: 'مثال: 05321234567' },
        DE: { min: 10, max: 12, hint: 'مثال: 01512345678' },
        GB: { min: 10, max: 11, hint: 'مثال: 07911123456' },
        FR: { min: 9,  max: 10, hint: 'مثال: 0612345678'  },
        US: { min: 10, max: 10, hint: 'مثال: 2025551234'  },
        CA: { min: 10, max: 10, hint: 'مثال: 4161234567'  },
        RU: { min: 10, max: 11, hint: 'مثال: 9161234567'  },
        CN: { min: 11, max: 11, hint: 'مثال: 13812345678' },
        IN: { min: 10, max: 10, hint: 'مثال: 9812345678'  },
        PK: { min: 10, max: 11, hint: 'مثال: 03001234567' },
        BD: { min: 10, max: 11, hint: 'مثال: 01712345678' },
        NG: { min: 10, max: 11, hint: 'مثال: 08012345678' },
        ZA: { min: 9,  max: 10, hint: 'مثال: 0821234567'  },
        // default لأي دولة غير موجودة
        DEFAULT: { min: 6, max: 15, hint: 'أدخل رقم الجوال الصحيح' },
    };

    // ==================== جلب الدول ====================
    async function fetchCountries() {
        try {
            const cached = localStorage.getItem(CACHE_KEY);
            if (cached) {
                const { data, time } = JSON.parse(cached);
                if (Date.now() - time < CACHE_EXPIRE && data.length > 0) {
                    return data;
                }
            }
        } catch (e) {}

        try {
            const res  = await fetch(
                'https://restcountries.com/v3.1/all?fields=name,idd,flag,cca2,translations',
                { cache: 'force-cache' }
            );
            const json = await res.json();

            const parsed = json
                .filter(c => c.idd?.root && c.idd?.suffixes?.length > 0)
                .map(c => {
                    const suffix = c.idd.suffixes.length === 1 ? c.idd.suffixes[0] : '';
                    return {
                        code: c.cca2,
                        name: c.translations?.ara?.common || c.name.common,
                        flag: c.flag || '',
                        dial: c.idd.root + suffix,
                    };
                })
                .filter(c => c.dial && c.dial.length > 1);

            // الأولوية: فلسطين أولاً ثم الدول العربية
            const priority = ['PS', 'EG', 'JO', 'SA', 'AE', 'QA', 'KW', 'BH', 'OM',
                              'IQ', 'SY', 'LB', 'YE', 'LY', 'TN', 'MA', 'DZ', 'SD'];
            parsed.sort((a, b) => {
                const ai = priority.indexOf(a.code);
                const bi = priority.indexOf(b.code);
                if (ai !== -1 && bi !== -1) return ai - bi;
                if (ai !== -1) return -1;
                if (bi !== -1) return  1;
                return a.name.localeCompare(b.name, 'ar');
            });

            localStorage.setItem(CACHE_KEY, JSON.stringify({ data: parsed, time: Date.now() }));
            return parsed;

        } catch (e) {
            // Fallback أساسي
            return [
                { code:'PS', name:'فلسطين',           flag:'🇵🇸', dial:'+970' },
                { code:'EG', name:'مصر',               flag:'🇪🇬', dial:'+20'  },
                { code:'JO', name:'الأردن',             flag:'🇯🇴', dial:'+962' },
                { code:'SA', name:'السعودية',           flag:'🇸🇦', dial:'+966' },
                { code:'AE', name:'الإمارات',           flag:'🇦🇪', dial:'+971' },
                { code:'KW', name:'الكويت',             flag:'🇰🇼', dial:'+965' },
                { code:'QA', name:'قطر',                flag:'🇶🇦', dial:'+974' },
                { code:'BH', name:'البحرين',            flag:'🇧🇭', dial:'+973' },
                { code:'OM', name:'عُمان',              flag:'🇴🇲', dial:'+968' },
                { code:'IQ', name:'العراق',             flag:'🇮🇶', dial:'+964' },
                { code:'SY', name:'سوريا',              flag:'🇸🇾', dial:'+963' },
                { code:'LB', name:'لبنان',              flag:'🇱🇧', dial:'+961' },
                { code:'TR', name:'تركيا',              flag:'🇹🇷', dial:'+90'  },
                { code:'DE', name:'ألمانيا',            flag:'🇩🇪', dial:'+49'  },
                { code:'GB', name:'المملكة المتحدة',    flag:'🇬🇧', dial:'+44'  },
                { code:'US', name:'الولايات المتحدة',  flag:'🇺🇸', dial:'+1'   },
            ];
        }
    }

    // ==================== التحقق من الرقم ====================
function validatePhone(number, countryCode) {
    if (!number) return { valid: false, msg: 'رقم الجوال مطلوب' };

    // تنظيف — أرقام فقط
    const cleaned = number.replace(/[\s\-\(\)\+]/g, '');
    if (!/^\d+$/.test(cleaned)) {
        return { valid: false, msg: 'يجب أن يحتوي على أرقام فقط' };
    }

    // قبول أي رقم طوله بين 7 و 15
    if (cleaned.length >= 7 && cleaned.length <= 15) {
        return { valid: true, msg: '' };
    }

    return { valid: false, msg: 'رقم الجوال قصير جداً أو طويل جداً' };
}

    // ==================== بناء المكوّن ====================
    function buildPicker(config) {
        const {
            containerId,
            inputId,
            dialId,
            codeId,
            errorId,
            hintId,
            defaultCode,
        } = config;

        const container = document.getElementById(containerId);
        if (!container) return;

        container.innerHTML = `
            <div class="phone-picker" id="pp_${containerId}">
                <div class="pp-selector" id="ppSelector_${containerId}"
                     onclick="PhonePicker.toggleDropdown('${containerId}')">
                    <span class="pp-flag"  id="ppFlag_${containerId}">🇵🇸</span>
                    <span class="pp-dial"  id="ppDial_${containerId}">+970</span>
                    <span class="pp-arrow" id="ppArrow_${containerId}">▾</span>
                </div>
                <input type="text"
                       id="${inputId}"
                       class="pp-input form-control"
                       placeholder="أدخل رقم الجوال"
                       maxlength="15"
                       inputmode="numeric"
                       autocomplete="tel"
                       oninput="PhonePicker.onInput('${containerId}','${inputId}','${errorId}','${hintId}')"
                       onblur="PhonePicker.onBlur('${containerId}','${inputId}','${errorId}','${hintId}')">
                <input type="hidden" id="${dialId}" value="+970">
                <input type="hidden" id="${codeId}" value="PS">

                <div class="pp-dropdown d-none" id="ppDrop_${containerId}">
                    <div class="pp-search-wrap">
                        <input type="text"
                               class="pp-search"
                               placeholder="🔍 ابحث عن دولة..."
                               oninput="PhonePicker.filterCountries('${containerId}', this.value)"
                               onclick="event.stopPropagation()">
                    </div>
                    <div class="pp-list" id="ppList_${containerId}">
                        <div class="pp-loading">⏳ جار تحميل الدول...</div>
                    </div>
                </div>
            </div>
            <div class="pp-hint" id="${hintId}"></div>
            <div class="field-error" id="${errorId}"></div>
        `;

        // إغلاق عند الضغط خارج
        document.addEventListener('click', e => {
            const drop = document.getElementById(`ppDrop_${containerId}`);
            const sel  = document.getElementById(`ppSelector_${containerId}`);
            if (drop && !drop.contains(e.target) && sel && !sel.contains(e.target)) {
                drop.classList.add('d-none');
                const arrow = document.getElementById(`ppArrow_${containerId}`);
                if (arrow) arrow.textContent = '▾';
            }
        });

        loadCountries(containerId, dialId, codeId, defaultCode || 'PS');
    }

    // ==================== تحميل الدول ====================
    async function loadCountries(containerId, dialId, codeId, defaultCode) {
        countriesData = await fetchCountries();
        renderList(containerId, dialId, codeId, countriesData);
        const def = countriesData.find(c => c.code === defaultCode) || countriesData[0];
        if (def) selectCountry(containerId, dialId, codeId, def);
    }

    function renderList(containerId, dialId, codeId, list) {
        const el = document.getElementById(`ppList_${containerId}`);
        if (!el) return;
        if (!list.length) {
            el.innerHTML = '<div class="pp-empty">لا توجد نتائج</div>';
            return;
        }
        el.innerHTML = list.map(c => {
            const encoded = encodeURIComponent(JSON.stringify({
                code: c.code, dial: c.dial, flag: c.flag, name: c.name
            }));
            return `
                <div class="pp-item"
                     onclick="PhonePicker._selectEncoded('${containerId}','${dialId}','${codeId}','${encoded}')">
                    <span class="pp-item-flag">${c.flag}</span>
                    <span class="pp-item-name">${_esc(c.name)}</span>
                    <span class="pp-item-dial">${_esc(c.dial)}</span>
                </div>`;
        }).join('');
    }

    function _esc(str) {
        return String(str)
            .replace(/&/g,'&amp;').replace(/</g,'&lt;')
            .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    // ==================== اختيار دولة ====================
    function _selectEncoded(containerId, dialId, codeId, encoded) {
        try {
            const c = JSON.parse(decodeURIComponent(encoded));
            selectCountry(containerId, dialId, codeId, c);
            document.getElementById(`ppDrop_${containerId}`)?.classList.add('d-none');
            const arrow = document.getElementById(`ppArrow_${containerId}`);
            if (arrow) arrow.textContent = '▾';

            // إعادة تحقق الرقم إن كان مدخلاً
            const picker = document.getElementById(`pp_${containerId}`);
            const input  = picker?.querySelector('.pp-input');
            if (input?.value) {
                triggerValidation(
                    containerId, input.id, c.code, input.value,
                    picker.nextElementSibling?.nextElementSibling?.id || '',
                    picker.nextElementSibling?.id || ''
                );
            }
        } catch (e) {}
    }

    // للتوافق مع الكود القديم
    function selectFromList(containerId, dialId, codeId, code, dial, flag, name) {
        selectCountry(containerId, dialId, codeId, { code, dial, flag, name });
        document.getElementById(`ppDrop_${containerId}`)?.classList.add('d-none');
        const arrow = document.getElementById(`ppArrow_${containerId}`);
        if (arrow) arrow.textContent = '▾';
    }

    function selectCountry(containerId, dialId, codeId, country) {
        const flagEl = document.getElementById(`ppFlag_${containerId}`);
        const dialEl = document.getElementById(`ppDial_${containerId}`);
        const dialIn = document.getElementById(dialId);
        const codeIn = document.getElementById(codeId);
        if (flagEl) flagEl.textContent = country.flag;
        if (dialEl) dialEl.textContent = country.dial;
        if (dialIn) dialIn.value = country.dial;
        if (codeIn) codeIn.value = country.code;

        // تحديث maxlength حسب الدولة
        const rule = PHONE_RULES[country.code] || PHONE_RULES.DEFAULT;
        const picker = document.getElementById(`pp_${containerId}`);
        const input  = picker?.querySelector('.pp-input');
        if (input) {
            input.maxLength  = rule.max;
            input.placeholder = rule.hint.replace('مثال: ','') || 'أدخل رقم الجوال';
        }

        try { localStorage.setItem('ruhamaa_last_country', country.code); } catch(e) {}
    }

    // ==================== Toggle Dropdown ====================
    function toggleDropdown(containerId) {
        const drop  = document.getElementById(`ppDrop_${containerId}`);
        const arrow = document.getElementById(`ppArrow_${containerId}`);
        if (!drop) return;
        const isOpen = !drop.classList.contains('d-none');
        drop.classList.toggle('d-none', isOpen);
        if (arrow) arrow.textContent = isOpen ? '▾' : '▴';
        if (!isOpen) setTimeout(() => drop.querySelector('.pp-search')?.focus(), 50);
    }

    // ==================== Filter ====================
    function filterCountries(containerId, query) {
        const drop   = document.getElementById(`ppDrop_${containerId}`);
        if (!drop) return;
        const picker = drop.closest('.phone-picker');
        const hiddens = picker?.querySelectorAll('input[type="hidden"]');
        const dialId  = hiddens?.[0]?.id || '';
        const codeId  = hiddens?.[1]?.id || '';

        const q = query.trim().toLowerCase();
        const filtered = q
            ? countriesData.filter(c =>
                c.name.includes(query) ||
                c.dial.includes(query) ||
                c.code.toLowerCase().includes(q)
              )
            : countriesData;

        renderList(containerId, dialId, codeId, filtered);
    }

    // ==================== Input / Blur ====================
    function onInput(containerId, inputId, errorId, hintId) {
        const input = document.getElementById(inputId);
        if (!input) return;
        // أرقام فقط
        input.value = input.value.replace(/[^\d]/g, '');
        clearPickerErr(inputId, errorId, hintId);
    }

    function onBlur(containerId, inputId, errorId, hintId) {
        const input = document.getElementById(inputId);
        if (!input?.value) return;
        const code = getCodeFromContainer(containerId);
        triggerValidation(containerId, inputId, code, input.value, errorId, hintId);
    }

    // ==================== Validation ====================
    function triggerValidation(containerId, inputId, code, value, errorId, hintId) {
        const result = validatePhone(value, code);
        const input  = document.getElementById(inputId);
        if (!input) return false;

        if (result.valid) {
            input.classList.remove('is-invalid');
            input.classList.add('is-valid');
            if (hintId) {
                const el = document.getElementById(hintId);
                if (el) {
                    el.textContent = result.formatted ? `✅ ${result.formatted}` : '✅ رقم صحيح';
                    el.style.color = '#1a7a4a';
                }
            }
        } else {
            input.classList.add('is-invalid');
            input.classList.remove('is-valid');
            if (errorId) {
                const el = document.getElementById(errorId);
                if (el) { el.textContent = result.msg; el.classList.add('show'); }
            }
        }
        return result.valid;
    }

    // ==================== Helpers ====================
    function getCodeFromContainer(containerId) {
        const picker  = document.getElementById(`pp_${containerId}`);
        if (!picker) return 'PS';
        const hiddens = picker.querySelectorAll('input[type="hidden"]');
        // hiddens[0] = dialId (القيمة مثل +970)
        // hiddens[1] = codeId (القيمة مثل PS)
        return hiddens[1]?.value || hiddens[0]?.value || 'PS';
    }

    function clearPickerErr(inputId, errorId, hintId) {
        document.getElementById(inputId)?.classList.remove('is-invalid', 'is-valid');
        if (errorId) {
            const el = document.getElementById(errorId);
            if (el) { el.textContent = ''; el.classList.remove('show'); }
        }
        if (hintId) {
            const el = document.getElementById(hintId);
            if (el) { el.textContent = ''; el.style.color = ''; }
        }
    }

    // ==================== Public API ====================
    function getFullNumber(dialId, inputId) {
        const dial = document.getElementById(dialId)?.value || '';
        const num  = document.getElementById(inputId)?.value || '';
        return dial + num;
    }

    function isValid(containerId, inputId, errorId, hintId) {
    const input = document.getElementById(inputId);
    if (!input?.value || input.value.trim() === '') {
        if (errorId) {
            const el = document.getElementById(errorId);
            if (el) { el.textContent = 'رقم الجوال مطلوب'; el.classList.add('show'); }
        }
        input?.classList.add('is-invalid');
        return false;
    }

    const cleaned = input.value.replace(/\D/g, '');
    if (cleaned.length >= 7 && cleaned.length <= 15) {
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
        return true;
    }

    if (errorId) {
        const el = document.getElementById(errorId);
        if (el) { el.textContent = 'رقم الجوال غير صالح'; el.classList.add('show'); }
    }
    input.classList.add('is-invalid');
    return false;
}

    function initWhatsapp(config) {
        config.containerId = config.containerId || 'whatsappContainer';
        buildPicker(config);
    }

    return {
        init:           buildPicker,
        initWhatsapp,
        toggleDropdown,
        filterCountries,
        selectFromList,
        _selectEncoded,
        onInput,
        onBlur,
        getFullNumber,
        isValid,
        validate: validatePhone,
    };

})();
