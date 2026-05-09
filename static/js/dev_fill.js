/**
 * dev_fill.js — تعبئة بيانات تجريبية لصفحة التسجيل
 * الاستخدام من الـ Console:
 *   fill('orphan')   — تعبئة بيانات يتيم
 *   fill('special')  — تعبئة بيانات ذوي احتياجات
 *   fill('family')   — تعبئة بيانات أسرة
 *   fill('sponsor')  — تعبئة بيانات كافل
 */

function fill(type) {

    // ── مساعدات ──────────────────────────────────────────
    const rand  = () => Math.floor(Math.random() * 9000) + 1000;
    const R     = rand();

    function _set(id, val) {
        const el = document.getElementById(id);
        if (!el) return;
        el.value = val;
        el.dispatchEvent(new Event('input',  { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function _selectCountry(key, code) {
        if (typeof allCountries === 'undefined') return;
        const c = allCountries.find(x => x.code === code);
        if (c && typeof ddSelect === 'function') ddSelect(key, c, false);
    }

    // ── الخطوة 1 — اختيار النوع ──────────────────────────
    const radio = document.querySelector(`input[name="userType"][value="${type}"]`);
    if (!radio) { console.error('النوع غير موجود:', type); return; }
    radio.checked = true;
    if (typeof selectType === 'function') selectType(type);

    // ── الخطوة 2 — البيانات المشتركة ─────────────────────
    _set('first_name',  'محمد');
    _set('father_name', 'أحمد');
    _set('grand_name',  'علي');
    _set('family_name', 'الحسن');
    _set('email',       `test${R}@test.com`);
    _set('gender',      'ذكر');
    _set('password',    'Test1234');
    _set('password2',   'Test1234');

    // الجنسية والمفاتيح
    _selectCountry('nat', 'PS');
    _selectCountry('p1',  'PS');
    _selectCountry('p2',  'PS');
    _selectCountry('wa',  'PS');

    _set('phone1',   `0591${R}23`);
    _set('whatsapp', `0592${R}45`);

    if (typeof checkPassStr   === 'function') checkPassStr();
    if (typeof checkPassMatch === 'function') checkPassMatch();

    // ── حسب النوع ────────────────────────────────────────
    if (type === 'sponsor')  _fillSponsor(R);
    if (type === 'orphan')   _fillOrphan(R);
    if (type === 'special')  _fillSpecial(R);
    if (type === 'family')   _fillFamily(R);

    console.log(`✅ تم تعبئة بيانات ${type} — R=${R}`);
}

// ══════════════════════════════════════════════════════════
// كافل
// ══════════════════════════════════════════════════════════
function _fillSponsor(R) {
    function _set(id, val) {
        const el = document.getElementById(id);
        if (!el) return;
        el.value = val;
        el.dispatchEvent(new Event('input',  { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
    }

    _set('username',     `sponsor${R}`);
    _set('sponsor_city', 'غزة');
    _set('sponsor_job',  'موظف حكومي');

    // الدولة
    if (typeof allCountries !== 'undefined' && typeof ddSelect === 'function') {
        const ps = allCountries.find(c => c.code === 'PS');
        if (ps) ddSelect('country', ps, false);
    }
}

// ══════════════════════════════════════════════════════════
// يتيم
// ══════════════════════════════════════════════════════════
function _fillOrphan(R) {
    function _set(id, val) {
        const el = document.getElementById(id);
        if (!el) return;
        el.value = val;
        el.dispatchEvent(new Event('input',  { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
    }

    // رقم الهوية
    _set('id_number', `9${R}12345`);

    // بيانات اليتيم
    _set('orphan_birth_date',      '2015-01-01');
    _set('orphan_orphan_type',     'يتيم الأب');
    _set('orphan_health_status',   'سليم');
    _set('orphan_education_level', 'ابتدائي');
    _set('orphan_school_name',     'مدرسة الأمل');

    // العنوان الحالي
    _set('orphan_current_city',     'مدينة غزة');
    _set('orphan_current_street',   'شارع النصر');
    _set('orphan_current_landmark', 'مسجد العمر');

    // العنوان السابق
    _set('orphan_previous_city',     'رفح');
    _set('orphan_previous_street',   'شارع الجلاء');
    _set('orphan_previous_landmark', 'مدرسة الرشاد');

    // السكن
    _set('orphan_housing_type',      'خيمة');
    _set('orphan_housing_ownership', 'ملك');

    // القصة
    _set('orphan_story', 'قصة اليتيم التجريبية — يتيم فقد والده في ظروف صعبة ويحتاج للرعاية والدعم.');

    // بيانات الأم
    _set('mother_first_name',      'فاطمة');
    _set('mother_father_name',     'خالد');
    _set('mother_grand_name',      'سعيد');
    _set('mother_family_name',     'الحسن');
    _set('mother_birth_date',      '1985-05-10');
    _set('mother_id_number',       `8${R}54321`);
    _set('mother_is_alive',        'true');
    _set('mother_health_status',   'سليمة');
    _set('mother_education_level', 'ثانوي');
    _set('mother_job',             'ربة بيت');
    _set('mother_monthly_income',  '500');

    // بيانات الأب
    _set('father_first_name',      'أحمد');
    _set('father_father_name',     'علي');
    _set('father_grand_name',      'حسن');
    _set('father_family_name',     'الحسن');
    _set('father_birth_date',      '1980-03-15');
    _set('father_id_number',       `9${R}99999`);
    _set('father_is_alive',        'false');
    _set('father_health_status',   'سليم');
    _set('father_education_level', 'جامعي');
    _set('father_job',             'معلم');
    _set('father_children_count',  '3');
    _set('father_death_reason',    'شهيد');
    _set('father_death_date',      '2023-10-07');

    // تفعيل toggle الأب
    const fatherAlive = document.getElementById('father_is_alive');
    if (fatherAlive && typeof toggleFatherDeath === 'function') {
        toggleFatherDeath(fatherAlive.value);
    }

    // بيانات المعيل
    _set('guardian_first_name',      'خالد');
    _set('guardian_father_name',     'محمد');
    _set('guardian_grand_name',      'أحمد');
    _set('guardian_family_name',     'الحسن');
    _set('guardian_id_number',       `4${R}11111`);
    _set('guardian_gender',          'ذكر');
    _set('guardian_relation',        'عم');
    _set('guardian_job',             'موظف حكومي');
    _set('guardian_health_status',   'سليم');
    _set('guardian_education_level', 'جامعي');
    _set('guardian_monthly_income',  '1200');
    _set('guardian_dependents',      '4');
}

// ══════════════════════════════════════════════════════════
// ذوو احتياجات خاصة
// ══════════════════════════════════════════════════════════
function _fillSpecial(R) {
    function _set(id, val) {
        const el = document.getElementById(id);
        if (!el) return;
        el.value = val;
        el.dispatchEvent(new Event('input',  { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
    }

    // رقم الهوية
    _set('id_number', `9${R}12345`);

    // بيانات المريض
    _set('special_birth_date',      '2010-06-15');
    _set('special_health_status',   'ذوو احتياجات خاصة');
    _set('special_education_level', 'ابتدائي');
    _set('special_school_name',     'مدرسة الأمل');

    // العنوان الحالي
    _set('special_current_city',     'مدينة غزة');
    _set('special_current_street',   'شارع الوحدة');
    _set('special_current_landmark', 'مستشفى الشفاء');

    // العنوان السابق
    _set('special_previous_city',     'خانيونس');
    _set('special_previous_street',   'شارع النصر');
    _set('special_previous_landmark', 'مسجد الرحمة');

    // السكن
    _set('special_housing_type',      'بيت باطون');
    _set('special_housing_ownership', 'ملك');

    // تفاصيل الحالة
    _set('special_case_details', 'يعاني المريض من إعاقة حركية منذ الولادة ويحتاج لكرسي متحرك ورعاية مستمرة.');

    // بيانات المعيل
    _set('special_guardian_first_name',      'سمير');
    _set('special_guardian_father_name',     'يوسف');
    _set('special_guardian_grand_name',      'حسن');
    _set('special_guardian_family_name',     'الحسن');
    _set('special_guardian_id_number',       `4${R}22222`);
    _set('special_guardian_gender',          'ذكر');
    _set('special_guardian_relation',        'أب');
    _set('special_guardian_job',             'عامل');
    _set('special_guardian_health_status',   'سليم');
    _set('special_guardian_education_level', 'ثانوي');
    _set('special_guardian_monthly_income',  '800');
    _set('special_guardian_dependents',      '5');
}

// ══════════════════════════════════════════════════════════
// أسرة
// ══════════════════════════════════════════════════════════
function _fillFamily(R) {
    function _set(id, val) {
        const el = document.getElementById(id);
        if (!el) return;
        el.value = val;
        el.dispatchEvent(new Event('input',  { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
    }

    // رقم الهوية
    _set('id_number', `9${R}12345`);

    // بيانات رب الأسرة
    _set('family_first_name',      'يوسف');
    _set('family_father_name_h',   'محمد');
    _set('family_grand_name_h',    'علي');
    _set('family_family_name_h',   'الحسن');
    _set('family_birth_date',      '1975-08-20');
    _set('family_id_number',       `9${R}12345`);
    _set('family_gender',          'ذكر');
    _set('family_marital_status',  'متزوج');
    _set('family_health_status',   'سليم');
    _set('family_education_level', 'جامعي');
    _set('family_job',             'موظف حكومي');
    _set('family_members_count',   '5');
    _set('family_sick_count',      '1');

    // تفعيل قسم الزوجة
    if (typeof toggleWifeSection === 'function') toggleWifeSection('متزوج');

    // العنوان الحالي
    _set('family_current_city',     'مدينة غزة');
    _set('family_current_street',   'شارع الجلاء');
    _set('family_current_landmark', 'مسجد الإسراء');

    // العنوان السابق
    _set('family_previous_city',     'بيت لاهيا');
    _set('family_previous_street',   'شارع النصر');
    _set('family_previous_landmark', 'مدرسة البراعم');

    // السكن
    _set('family_housing_type',      'خيمة');
    _set('family_housing_ownership', 'ملك');

    // الوضع العام
    _set('family_general_status', 'أسرة نازحة من شمال غزة تعاني من ظروف صعبة وتحتاج للدعم والمساعدة العاجلة.');

    // بيانات الزوجة
    _set('wife_first_name',      'مريم');
    _set('wife_father_name',     'خالد');
    _set('wife_grand_name',      'سعيد');
    _set('wife_family_name',     'النجار');
    _set('wife_birth_date',      '1980-03-12');
    _set('wife_id_number',       `8${R}33333`);
    _set('wife_health_status',   'سليمة');
    _set('wife_education_level', 'ثانوي');

    // بيانات المعيل
    _set('family_guardian_first_name',      'سالم');
    _set('family_guardian_father_name',     'أحمد');
    _set('family_guardian_grand_name',      'علي');
    _set('family_guardian_family_name',     'الحسن');
    _set('family_guardian_id_number',       `4${R}44444`);
    _set('family_guardian_gender',          'ذكر');
    _set('family_guardian_relation',        'أخ');
    _set('family_guardian_job',             'تاجر');
    _set('family_guardian_health_status',   'سليم');
    _set('family_guardian_education_level', 'جامعي');
    _set('family_guardian_monthly_income',  '2000');
    _set('family_guardian_dependents',      '3');
}

console.log('✅ dev_fill.js loaded — استخدم: fill("orphan") | fill("special") | fill("family") | fill("sponsor")');
