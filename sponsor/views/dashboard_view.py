"""
sponsor/views/dashboard_view.py
لوحة الرئيسية — الكافل
"""
from functools import wraps
from datetime import date, timedelta
import random

from django.shortcuts import render, redirect
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone

from core.models import CustomUser, Notification, Payment, DirectMessage
from sponsor.models import SponsorProfile, PaymentReceipt
from core.utils import get_exchange_rates


def sponsor_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/login/')
        if request.user.user_type != 'sponsor':
            return redirect('/login/')
        if not request.user.is_approved:
            return render(request, 'sponsor/pending.html')
        return view_func(request, *args, **kwargs)
    return wrapper


def _get_profile(user):
    try:
        return user.sponsor_profile
    except Exception:
        p, _ = SponsorProfile.objects.get_or_create(user=user)
        return p


def _profile_completion(user, profile):
    fields = [
        user.first_name, user.father_name, user.grand_name, user.family_name,
        user.email, user.phone, user.id_number, user.nationality,
        user.gender, profile.job, profile.country, profile.city, profile.whatsapp,
    ]
    if profile.photo or user.profile_image:
        fields.append('photo')
    filled = sum(1 for f in fields if f)
    return round(filled / len(fields) * 100)


def _get_badges(user, profile, stats):
    badges = []
    days_since = (timezone.now() - user.date_joined).days if user.date_joined else 0
    if stats['my_total'] >= 1:
        badges.append({'icon': '❤️', 'title': 'أول كفالة',        'color': '#1a7a4a'})
    if stats['my_total'] >= 5:
        badges.append({'icon': '🌟', 'title': 'كافل نشيط',        'color': '#2b6cb0'})
    if stats['my_total'] >= 10:
        badges.append({'icon': '👑', 'title': 'كافل متميز',       'color': '#b45309'})
    if days_since >= 365:
        badges.append({'icon': '🎖️', 'title': 'كافل منذ سنة',    'color': '#7c3aed'})
    if stats['paid_count'] >= 10:
        badges.append({'icon': '💎', 'title': '10 دفعات متتالية', 'color': '#1a7a4a'})
    if stats['commitment_pct'] == 100:
        badges.append({'icon': '🏆', 'title': 'التزام كامل',      'color': '#b45309'})
    return badges


# ══ الأحاديث والآيات — 10 أحاديث + 10 آيات بالتشكيل ══
QUOTES = [
    # أحاديث
    {'text': '«مَنْ كَفَلَ يَتِيمًا لَهُ أَوْ لِغَيْرِهِ كُنْتُ أَنَا وَهُوَ فِي الْجَنَّةِ كَهَاتَيْنِ»\nوَأَشَارَ بِالسَّبَّابَةِ وَالْوُسْطَى', 'source': 'رواه مسلم', 'type': 'hadith'},
    {'text': '«السَّاعِي عَلَى الأَرْمَلَةِ وَالْمِسْكِينِ كَالْمُجَاهِدِ فِي سَبِيلِ اللهِ، وَكَالَّذِي يَصُومُ النَّهَارَ وَيَقُومُ اللَّيْلَ»', 'source': 'متفق عليه', 'type': 'hadith'},
    {'text': '«مَا نَقَصَتْ صَدَقَةٌ مِنْ مَالٍ، وَمَا زَادَ اللهُ عَبْدًا بِعَفْوٍ إِلَّا عِزًّا»', 'source': 'رواه مسلم', 'type': 'hadith'},
    {'text': '«اتَّقُوا النَّارَ وَلَوْ بِشِقِّ تَمْرَةٍ، فَمَنْ لَمْ يَجِدْ فَبِكَلِمَةٍ طَيِّبَةٍ»', 'source': 'متفق عليه', 'type': 'hadith'},
    {'text': '«صَدَقَةُ السِّرِّ تُطْفِئُ غَضَبَ الرَّبِّ تَبَارَكَ وَتَعَالَى»', 'source': 'رواه الطبراني', 'type': 'hadith'},
    {'text': '«أَفْضَلُ الصَّدَقَةِ أَنْ تُصَدِّقَ وَأَنْتَ صَحِيحٌ شَحِيحٌ، تَأْمُلُ الْغِنَى وَتَخْشَى الْفَقْرَ»', 'source': 'متفق عليه', 'type': 'hadith'},
    {'text': '«كُلُّ سُلَامَى مِنَ النَّاسِ عَلَيْهِ صَدَقَةٌ كُلَّ يَوْمٍ تَطْلُعُ فِيهِ الشَّمْسُ»', 'source': 'متفق عليه', 'type': 'hadith'},
    {'text': '«خَيْرُ بَيْتٍ فِي الْمُسْلِمِينَ بَيْتٌ فِيهِ يَتِيمٌ يُحْسَنُ إِلَيْهِ، وَشَرُّ بَيْتٍ فِي الْمُسْلِمِينَ بَيْتٌ فِيهِ يَتِيمٌ يُسَاءُ إِلَيْهِ»', 'source': 'رواه ابن ماجه', 'type': 'hadith'},
    {'text': '«مَنْ أَدْخَلَ فَرَحًا عَلَى مُؤْمِنٍ فَقَدْ سَرَّنِي، وَمَنْ سَرَّنِي فَقَدِ اتَّخَذَ عِنْدَ اللهِ عَهْدًا»', 'source': 'رواه الطبراني', 'type': 'hadith'},
    {'text': '«إِذَا مَاتَ الإِنْسَانُ انْقَطَعَ عَمَلُهُ إِلَّا مِنْ ثَلَاثٍ: صَدَقَةٌ جَارِيَةٌ، أَوْ عِلْمٌ يُنْتَفَعُ بِهِ، أَوْ وَلَدٌ صَالِحٌ يَدْعُو لَهُ»', 'source': 'رواه مسلم', 'type': 'hadith'},
    # آيات
    {'text': '﴿وَيُطْعِمُونَ الطَّعَامَ عَلَى حُبِّهِ مِسْكِينًا وَيَتِيمًا وَأَسِيرًا﴾', 'source': 'سورة الإنسان — ٨', 'type': 'quran'},
    {'text': '﴿أَرَأَيْتَ الَّذِي يُكَذِّبُ بِالدِّينِ ❊ فَذَلِكَ الَّذِي يَدُعُّ الْيَتِيمَ ❊ وَلَا يَحُضُّ عَلَى طَعَامِ الْمِسْكِينِ﴾', 'source': 'سورة الماعون — ١-٣', 'type': 'quran'},
    {'text': '﴿وَفِي أَمْوَالِهِمْ حَقٌّ لِّلسَّائِلِ وَالْمَحْرُومِ﴾', 'source': 'سورة الذاريات — ١٩', 'type': 'quran'},
    {'text': '﴿مَّثَلُ الَّذِينَ يُنفِقُونَ أَمْوَالَهُمْ فِي سَبِيلِ اللَّهِ كَمَثَلِ حَبَّةٍ أَنبَتَتْ سَبْعَ سَنَابِلَ فِي كُلِّ سُنبُلَةٍ مِّائَةُ حَبَّةٍ﴾', 'source': 'سورة البقرة — ٢٦١', 'type': 'quran'},
    {'text': '﴿لَن تَنَالُوا الْبِرَّ حَتَّى تُنفِقُوا مِمَّا تُحِبُّونَ﴾', 'source': 'سورة آل عمران — ٩٢', 'type': 'quran'},
    {'text': '﴿وَمَا تُنفِقُوا مِنْ خَيْرٍ فَلِأَنفُسِكُمْ وَمَا تُنفِقُونَ إِلَّا ابْتِغَاءَ وَجْهِ اللَّهِ﴾', 'source': 'سورة البقرة — ٢٧٢', 'type': 'quran'},
    {'text': '﴿الَّذِينَ يُنفِقُونَ أَمْوَالَهُم بِاللَّيْلِ وَالنَّهَارِ سِرًّا وَعَلَانِيَةً فَلَهُمْ أَجْرُهُمْ عِندَ رَبِّهِمْ﴾', 'source': 'سورة البقرة — ٢٧٤', 'type': 'quran'},
    {'text': '﴿وَيَسْأَلُونَكَ مَاذَا يُنفِقُونَ قُلِ الْعَفْوَ﴾', 'source': 'سورة البقرة — ٢١٩', 'type': 'quran'},
    {'text': '﴿إِنَّ الَّذِينَ يَتْلُونَ كِتَابَ اللَّهِ وَأَقَامُوا الصَّلَاةَ وَأَنفَقُوا مِمَّا رَزَقْنَاهُمْ سِرًّا وَعَلَانِيَةً يَرْجُونَ تِجَارَةً لَّن تَبُورَ﴾', 'source': 'سورة فاطر — ٢٩', 'type': 'quran'},
    {'text': '﴿فَأَمَّا الْيَتِيمَ فَلَا تَقْهَرْ ❊ وَأَمَّا السَّائِلَ فَلَا تَنْهَرْ﴾', 'source': 'سورة الضحى — ٩-١٠', 'type': 'quran'},
]

DID_YOU_KNOW = [
    'كفالة اليتيم من أعظم أعمال البر وأجلّها عند الله تعالى.',
    'الكافل لليتيم في الجنة كالأصبعين المتلاصقين — الوسطى والسبابة.',
    'كفالة اليتيم تُطهّر القلب وتُليّنه وتجلب البركة في الرزق.',
    'الصدقة الجارية لا تنقطع حتى بعد الموت وأجرها يجري للمتصدق.',
    'خير بيت في المسلمين بيت فيه يتيم يُحسن إليه.',
    'من أعال ثلاثة من الأيتام كان كالقائم ليله وكالصائم نهاره.',
    'الصدقة تدفع البلاء وتطفئ غضب الرب وتشفي المريض.',
    'إن الله يُحب العبد الذي يمسح رأس اليتيم ابتغاء وجهه.',
    'الكافل والمكفول كلاهما مأجور — الكافل بعطائه والمكفول بصبره.',
    'كفالة اليتيم من أقرب الطرق إلى قلب النبي ﷺ.',
]


def _get_random_quote():
    return random.choice(QUOTES)


def _get_random_did_know():
    return random.choice(DID_YOU_KNOW)


@sponsor_required
def dashboard(request):
    user    = request.user
    profile = _get_profile(user)
    rates   = get_exchange_rates()
    today   = date.today()

    from beneficiary.models import OrphanForm, SpecialNeedsForm, FamilyForm

    # ══ المكفولون ══
    orphans_qs  = OrphanForm.objects.filter(sponsor=profile).select_related('user')
    specials_qs = SpecialNeedsForm.objects.filter(sponsor=profile).select_related('user')
    families_qs = FamilyForm.objects.filter(sponsor=profile).select_related('user')

    my_orphans  = orphans_qs.count()
    my_specials = specials_qs.count()
    my_families = families_qs.count()
    my_total    = my_orphans + my_specials + my_families

    # قائمة المكفولين المختصرة
    benes_list = []
    for f, label in (
        [(f, 'يتيم')       for f in orphans_qs[:4]] +
        [(f, 'ذو احتياج') for f in specials_qs[:2]] +
        [(f, 'أسرة')      for f in families_qs[:2]]
    ):
        last_pay = Payment.objects.filter(
            sponsor=user, beneficiary=f.user, status='paid'
        ).order_by('-date').first()
        late = Payment.objects.filter(
            sponsor=user, beneficiary=f.user, status='late'
        ).exists()
        benes_list.append({
            'name':     f.get_full_name(),
            'type':     label,
            'city':     getattr(f, 'current_city', None) or '—',
            'last_pay': str(last_pay.date) if last_pay else '—',
            'is_late':  late,
        })

    # ══ الدفعات ══
    pays_all   = Payment.objects.filter(sponsor=user)
    paid_qs    = pays_all.filter(status='paid')
    late_qs    = pays_all.filter(status='late')
    paid_count = paid_qs.count()
    late_count = late_qs.count()
    total_expected = paid_count + late_count
    commitment_pct = round(paid_count / total_expected * 100) if total_expected > 0 else 100

    total_shekel = paid_qs.aggregate(t=Sum('amount_ils'))['t'] or 0
    total_dollar = paid_qs.aggregate(t=Sum('amount_usd'))['t'] or 0

    # مقارنة الأشهر
    this_month_date = today.replace(day=1)
    last_month_date = (this_month_date - timedelta(days=1)).replace(day=1)
    this_month_ils  = paid_qs.filter(
        date__year=this_month_date.year, date__month=this_month_date.month
    ).aggregate(t=Sum('amount_ils'))['t'] or 0
    last_month_ils  = paid_qs.filter(
        date__year=last_month_date.year, date__month=last_month_date.month
    ).aggregate(t=Sum('amount_ils'))['t'] or 0
    month_diff_pct  = 0
    if last_month_ils > 0:
        month_diff_pct = round((float(this_month_ils) - float(last_month_ils)) / float(last_month_ils) * 100)

    # آخر دفعة
    last_payment = paid_qs.select_related('beneficiary').order_by('-date').first()

    # المخطط — آخر 6 أشهر
    chart_labels, chart_data = [], []
    for i in range(5, -1, -1):
        d = (today.replace(day=1) - timedelta(days=i * 30))
        t = paid_qs.filter(date__year=d.year, date__month=d.month).aggregate(
            t=Sum('amount_ils'))['t'] or 0
        chart_labels.append(f'{d.year}/{d.month:02d}')
        chart_data.append(float(t))

    # مقياس التأثير
    avg_all = Payment.objects.filter(status='paid').aggregate(a=Avg('amount_ils'))['a'] or 0
    my_avg  = paid_qs.aggregate(a=Avg('amount_ils'))['a'] or 0
    impact_pct = min(round((float(my_avg) / float(avg_all) * 100) if avg_all > 0 else 100), 200)

    # ══ الوصولات ══
    receipts_all = PaymentReceipt.objects.filter(sponsor=profile)
    rec_approved = receipts_all.filter(status='موافق').count()
    rec_rejected = receipts_all.filter(status='مرفوض').count()
    rec_pending  = receipts_all.filter(status='بانتظار المراجعة').count()
    last_receipt = receipts_all.order_by('-submitted_at').first()

    # ══ آخر رسالة من الإدارة ══
    last_admin_msg = DirectMessage.objects.filter(
        sender__user_type='admin', recipient=user
    ).order_by('-created_at').first()

    # ══ الإشعارات ══
    notifications = Notification.objects.filter(recipient=user).order_by('-created_at')[:5]
    notif_count   = Notification.objects.filter(recipient=user, is_read=False).count()

    # ══ الإعلانات ══
    try:
        from sponsor.models import Announcement
        announcements = Announcement.objects.filter(
            is_active=True, target__in=['all', 'sponsors']
        ).order_by('-created_at')[:3]
    except Exception:
        announcements = []

    # ══ دفعات متأخرة ══
    has_late = late_count > 0

    # ══ الإنجازات ══
    stats = {'my_total': my_total, 'paid_count': paid_count, 'commitment_pct': commitment_pct}
    badges     = _get_badges(user, profile, stats)
    completion = _profile_completion(user, profile)
    quote      = _get_random_quote()
    did_know   = _get_random_did_know()

    return render(request, 'sponsor/dashboard.html', {
        'profile':        profile,
        'completion':     completion,
        'badges':         badges,
        'my_total':       my_total,
        'my_orphans':     my_orphans,
        'my_specials':    my_specials,
        'my_families':    my_families,
        'benes_list':     benes_list,
        'total_shekel':   round(float(total_shekel), 2),
        'total_dollar':   round(float(total_dollar), 2),
        'commitment_pct': commitment_pct,
        'paid_count':     paid_count,
        'late_count':     late_count,
        'this_month_ils': round(float(this_month_ils), 2),
        'last_month_ils': round(float(last_month_ils), 2),
        'month_diff_pct': month_diff_pct,
        'last_payment':   last_payment,
        'chart_labels':   chart_labels,
        'chart_data':     chart_data,
        'impact_pct':     impact_pct,
        'rec_approved':   rec_approved,
        'rec_rejected':   rec_rejected,
        'rec_pending':    rec_pending,
        'last_receipt':   last_receipt,
        'last_admin_msg': last_admin_msg,
        'notifications':  notifications,
        'notif_count':    notif_count,
        'announcements':  announcements,
        'has_late':       has_late,
        'quote':          quote,
        'did_know':       did_know,
        'rates':          rates,
    })
