
from functools import wraps
from datetime import date

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_protect
from django.core.paginator import Paginator
from django.db.models import Q

from core.models import CustomUser, Notification
from sponsor.models import SponsorProfile
from core.utils import log_activity, create_notification, notify_admins

PER_PAGE = 20


# ══ Decorator ══
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
        profile, _ = SponsorProfile.objects.get_or_create(user=user)
        return profile


# ══════════════════════════════════════════════════════════
# الصفحة الرئيسية
# ══════════════════════════════════════════════════════════

@sponsor_required
def orphans(request):
    from beneficiary.models import OrphanForm, SpecialNeedsForm, FamilyForm

    user = request.user
    notif_count = Notification.objects.filter(recipient=user, is_read=False).count()

    free_orphans_count  = OrphanForm.objects.filter(sponsor__isnull=True, user__is_approved=True).count()
    free_specials_count = SpecialNeedsForm.objects.filter(sponsor__isnull=True, user__is_approved=True).count()
    free_families_count = FamilyForm.objects.filter(sponsor__isnull=True, user__is_approved=True).count()

    return render(request, 'sponsor/orphans.html', {
        'notif_count':        notif_count,
        'free_orphans_count': free_orphans_count,
        'free_specials_count':free_specials_count,
        'free_families_count':free_families_count,
        'free_total':         free_orphans_count + free_specials_count + free_families_count,
    })


# ══════════════════════════════════════════════════════════
# AJAX — بيانات التاب
# ══════════════════════════════════════════════════════════

@sponsor_required
@require_GET
def free_data(request):
    from beneficiary.models import OrphanForm, SpecialNeedsForm, FamilyForm

    tab  = request.GET.get('tab',  'orphan')
    page = int(request.GET.get('page', 1))
    q    = request.GET.get('q', '').strip()

    MAP = {
        'orphan':  (OrphanForm,       _serialize_orphan),
        'special': (SpecialNeedsForm, _serialize_special),
        'family':  (FamilyForm,       _serialize_family),
    }
    if tab not in MAP:
        return JsonResponse({'items': [], 'total': 0, 'pages': 0, 'current_page': 1})

    Model, serializer = MAP[tab]
    qs = Model.objects.filter(
        sponsor__isnull=True, user__is_approved=True
    ).select_related('user').order_by('-user__date_joined')

    if q:
        qs = qs.filter(
            Q(first_name__icontains=q)  | Q(father_name__icontains=q) |
            Q(family_name__icontains=q) | Q(id_number__icontains=q)   |
            Q(form_number__icontains=q) | Q(user__registration_number__icontains=q)
        )

    # ── فلاتر إضافية ──
    gender      = request.GET.get('gender',       '').strip()
    city        = request.GET.get('city',         '').strip()
    housing     = request.GET.get('housing_type', '').strip()
    age_range   = request.GET.get('age_range',    '').strip()
    health      = request.GET.get('health',       '').strip()
    sort        = request.GET.get('sort',         'newest').strip()
    orphan_type = request.GET.get('orphan_type',  '').strip()

    if gender:      qs = qs.filter(gender=gender)
    if city:        qs = qs.filter(current_city=city)
    if housing:     qs = qs.filter(housing_type=housing)
    if health:      qs = qs.filter(health_status=health)
    if orphan_type and tab == 'orphan': qs = qs.filter(orphan_type=orphan_type)

    # فلتر العمر
    if age_range:
        from django.utils import timezone
        today = timezone.now().date()
        import datetime
        ranges = {'0-5':(0,5),'6-12':(6,12),'13-18':(13,18),'18+':(18,200)}
        rng = ranges.get(age_range)
        if rng:
            max_date = today.replace(year=today.year - rng[0])
            min_date = today.replace(year=today.year - rng[1]) if rng[1] < 200 else datetime.date(1900,1,1)
            qs = qs.filter(birth_date__range=(min_date, max_date))

    # الترتيب
    order_map = {'newest':'-user__date_joined','oldest':'user__date_joined','name':'first_name'}
    qs = qs.order_by(order_map.get(sort, '-user__date_joined'))

    # filter_options — قيم فريدة من القاعدة للتاب الحالي
    base_qs = Model.objects.filter(sponsor__isnull=True, user__is_approved=True)
    filter_options = {
        'cities':          list(base_qs.exclude(current_city='').values_list('current_city',flat=True).distinct().order_by('current_city')),
        'housing_types':   list(base_qs.exclude(housing_type='').values_list('housing_type',flat=True).distinct().order_by('housing_type')),
        'health_statuses': list(base_qs.exclude(health_status='').values_list('health_status',flat=True).distinct().order_by('health_status')),
    }

    # is_new — مضاف خلال آخر 7 أيام
    from django.utils import timezone as tz
    week_ago = tz.now() - __import__('datetime').timedelta(days=7)

    paginator = Paginator(qs, PER_PAGE)
    pg = paginator.get_page(page)

    items = []
    for obj in pg:
        item = serializer(obj)
        item['is_new'] = obj.user.date_joined >= week_ago if obj.user.date_joined else False
        items.append(item)

    return JsonResponse({
        'items':          items,
        'total':          paginator.count,
        'pages':          paginator.num_pages,
        'current_page':   pg.number,
        'filter_options': filter_options,
    })


# ══════════════════════════════════════════════════════════
# AJAX — تفاصيل — يستخدم admin_panel._user_detail مباشرة
# ══════════════════════════════════════════════════════════

@sponsor_required
@require_GET
def free_detail(request):
    from beneficiary.models import OrphanForm, SpecialNeedsForm, FamilyForm

    tab = request.GET.get('tab', 'orphan')
    pk  = request.GET.get('id',  0)

    MAP = {'orphan': OrphanForm, 'special': SpecialNeedsForm, 'family': FamilyForm}
    Model = MAP.get(tab)
    if not Model:
        return JsonResponse({'error': 'نوع غير صالح'}, status=400)

    obj = get_object_or_404(Model, pk=pk, sponsor__isnull=True, user__is_approved=True)

    try:
        from admin_panel.views.requests import _user_detail
        user   = obj.user
        detail = _user_detail(user)
    except Exception as e:
        return JsonResponse({'error': f'خطأ: {str(e)}'}, status=500)

    photo = ''
    try:
        if obj.photo:
            photo = obj.photo.url
    except Exception:
        pass

    user_data = {
        'id':          str(user.pk),
        'full_name':   user.get_full_name(),
        'email':       user.email or '',
        'phone':       f'{user.phone_country or ""}{user.phone or ""}',
        'id_number':   user.id_number or '',
        'nationality': user.nationality or '',
        'gender':      user.gender or '',
        'reg_number':  user.registration_number or '',
        'date_joined': user.date_joined.strftime('%Y/%m/%d %H:%M') if user.date_joined else '',
        'last_login':  user.last_login.strftime('%Y/%m/%d %H:%M') if user.last_login else '',
        'is_active':   user.is_active,
        'photo':       photo,
        'user_type':   user.user_type,
        'tab':         tab,
        'form_id':     obj.pk,
    }

    return JsonResponse({'status': 'ok', 'detail': detail, 'user': user_data})


# ══════════════════════════════════════════════════════════
# AJAX — تنفيذ الكفالة
# ══════════════════════════════════════════════════════════

@sponsor_required
@require_POST
@csrf_protect
def do_sponsor(request):
    from beneficiary.models import OrphanForm, SpecialNeedsForm, FamilyForm

    tab     = request.POST.get('tab', '')
    pk      = request.POST.get('id',  0)
    user    = request.user
    profile = _get_profile(user)

    MAP = {'orphan': OrphanForm, 'special': SpecialNeedsForm, 'family': FamilyForm}
    Model = MAP.get(tab)
    if not Model:
        return JsonResponse({'status': 'error', 'message': 'نوع غير صالح'})

    obj = get_object_or_404(Model, pk=pk, sponsor__isnull=True, user__is_approved=True)
    obj.sponsor          = profile
    obj.status           = 'تم التكفل'
    obj.sponsorship_date = date.today()
    obj.save()

    log_activity(user, 'SPONSOR',
                 description=f'تكفّل بـ {obj.get_full_name()} [{obj.form_number}]',
                 request=request)

    notify_admins(ntype='NEW_SPONSOR', title='كفالة جديدة 🤝',
                  message=f'{user.get_full_name()} تكفّل بـ {obj.get_full_name()}',
                  sender=user, action_url='/admin-panel/beneficiaries/')

    create_notification(recipient=obj.user, ntype='SYSTEM',
                        title='تم اختيارك للكفالة 🎉',
                        message=f'قام الكافل {user.get_full_name()} بالتكفل بك',
                        sender=user)

    return JsonResponse({'status': 'success', 'message': f'تم التكفل بـ {obj.get_full_name()} بنجاح ✅'})


# ══════════════════════════════════════════════════════════
# طباعة — نفس مسار لوحة الأدمن
# ══════════════════════════════════════════════════════════

@sponsor_required
def print_beneficiary(request):
    from beneficiary.models import OrphanForm, SpecialNeedsForm, FamilyForm
    from django.template.loader import render_to_string
    from django.http import HttpResponse

    tab = request.GET.get('tab', 'orphan')
    pk  = request.GET.get('id',  0)

    MAP = {'orphan': OrphanForm, 'special': SpecialNeedsForm, 'family': FamilyForm}
    Model = MAP.get(tab)
    if not Model:
        return redirect('/sponsor/free/')

    obj  = get_object_or_404(Model, pk=pk)
    user = obj.user

    try:
        from admin_panel.views.requests import _user_detail
        detail = _user_detail(user)
    except Exception as e:
        return HttpResponse(f'خطأ: {str(e)}', status=500)

    html = render_to_string('admin_panel/print_request.html', {
        'user':       user,
        'detail':     detail,
        'printed_by': request.user.get_full_name() or request.user.username,
        'request':    request,
    })
    return HttpResponse(html)


@sponsor_required
def download_pdf(request):
    from beneficiary.models import OrphanForm, SpecialNeedsForm, FamilyForm
    from django.template.loader import render_to_string
    from django.http import HttpResponse
    from urllib.parse import quote
    import weasyprint, logging

    logging.getLogger('weasyprint').setLevel(logging.ERROR)
    logging.getLogger('fontTools').setLevel(logging.ERROR)

    tab = request.GET.get('tab', 'orphan')
    pk  = request.GET.get('id',  0)

    MAP = {'orphan': OrphanForm, 'special': SpecialNeedsForm, 'family': FamilyForm}
    Model = MAP.get(tab)
    if not Model:
        return redirect('/sponsor/free/')

    obj  = get_object_or_404(Model, pk=pk)
    user = obj.user

    try:
        from admin_panel.views.requests import _user_detail
        detail = _user_detail(user)
    except Exception as e:
        return HttpResponse(f'خطأ: {str(e)}', status=500)

    html_content = render_to_string('admin_panel/pdf_request.html', {
        'user':       user,
        'detail':     detail,
        'printed_by': request.user.get_full_name() or request.user.username,
        'request':    request,
    })

    pdf_file = weasyprint.HTML(
        string=html_content,
        base_url=request.build_absolute_uri('/')
    ).write_pdf()

    name   = user.get_full_name().replace(' ', '_')
    id_num = user.id_number or user.username or str(user.pk)[:8]
    fname  = f'{name}_{id_num}.pdf'

    resp = HttpResponse(pdf_file, content_type='application/pdf')
    resp['Content-Disposition'] = f"attachment; filename*=UTF-8''{quote(fname)}"
    return resp


# ══════════════════════════════════════════════════════════
# Serializers
# ══════════════════════════════════════════════════════════

def _photo(obj):
    try:
        return obj.photo.url if obj.photo else ''
    except Exception:
        return ''


def _serialize_orphan(o):
    return {
        'id': o.pk, 'user_id': str(o.user_id), 'tab': 'orphan',
        'reg_number':  o.user.registration_number or '',
        'form_number': o.form_number,
        'full_name':   o.get_full_name(),
        'photo':       _photo(o),
        'gender':      o.gender or '',
        'birth_date':  str(o.birth_date) if o.birth_date else '',
        'orphan_type': o.orphan_type or '',
        'current_city':o.current_city or '',
        'health_status':  o.health_status or '',
        'education_level':o.education_level or '',
        'id_number':   o.id_number or '',
        'housing_type':o.housing_type or '',
    }


def _serialize_special(s):
    return {
        'id': s.pk, 'user_id': str(s.user_id), 'tab': 'special',
        'reg_number':  s.user.registration_number or '',
        'form_number': s.form_number,
        'full_name':   s.get_full_name(),
        'photo':       _photo(s),
        'gender':      s.gender or '',
        'birth_date':  str(s.birth_date) if s.birth_date else '',
        'current_city':   s.current_city or '',
        'health_status':  s.health_status or '',
        'case_details':   (s.case_details or '')[:60],
        'education_level':s.education_level or '',
        'id_number':   s.id_number or '',
        'housing_type':s.housing_type or '',
    }


def _serialize_family(f):
    return {
        'id': f.pk, 'user_id': str(f.user_id), 'tab': 'family',
        'reg_number':  f.user.registration_number or '',
        'form_number': f.form_number,
        'full_name':   f.get_full_name(),
        'photo':       _photo(f),
        'gender':      f.gender or '',
        'birth_date':  str(f.birth_date) if f.birth_date else '',
        'current_city':    f.current_city or '',
        'health_status':   f.health_status or '',
        'members_count':   f.family_members_count or 0,
        'general_status':  (f.general_status or '')[:60],
        'id_number':   f.id_number or '',
        'housing_type':f.housing_type or '',
    }
@sponsor_required
@require_POST
@csrf_protect
def info_request(request):
    from beneficiary.models import OrphanForm, SpecialNeedsForm, FamilyForm
    from core.models import DirectMessage, CustomUser

    tab = request.POST.get('tab', '')
    pk  = request.POST.get('id',  0)
    msg = request.POST.get('message', '').strip()

    if not msg:
        return JsonResponse({'status': 'error', 'message': 'الرسالة فارغة'})

    MAP = {'orphan': OrphanForm, 'special': SpecialNeedsForm, 'family': FamilyForm}
    Model = MAP.get(tab)
    if not Model:
        return JsonResponse({'status': 'error', 'message': 'نوع غير صالح'})

    obj  = get_object_or_404(Model, pk=pk)
    user = request.user

    # نفس منطق اختيار الأدمن في messages_view
    admin = CustomUser.objects.filter(
        user_type='admin', is_active=True,
        sent_direct_messages__recipient=user
    ).first()

    if not admin:
        admin = CustomUser.objects.filter(
            user_type='admin', is_active=True, is_staff=True
        ).first()

    if not admin:
        admin = CustomUser.objects.filter(
            user_type='admin', is_active=True
        ).order_by('-date_joined').first()

    if not admin:
        return JsonResponse({'status': 'error', 'message': 'لا يوجد أدمن متاح'})

    # رقم التسجيل
    reg_number = obj.user.registration_number or obj.form_number

    # تنسيق الرسالة
    full_msg = (
        f"📩 طلب معلومات\n"
        f"─────────────────\n"
        f"👤 المستفيد: {obj.get_full_name()}\n"
        f"📋 رقم التسجيل: {reg_number}\n"
        f"─────────────────\n"
        f"💬 السؤال:\n"
        f"{msg}"
    )

    DirectMessage.objects.create(
        sender    = user,
        recipient = admin,
        message   = full_msg,
    )

    create_notification(
        recipient  = admin,
        ntype      = 'NEW_MSG',
        title      = 'طلب معلومات من كافل 📩',
        message    = f'{user.get_full_name()} يسأل عن {obj.get_full_name()}',
        sender     = user,
        action_url = '/admin-panel/messages/',
    )

    log_activity(
        user, 'MESSAGE',
        description = f'طلب معلومات عن {obj.get_full_name()} [{reg_number}]',
        request     = request,
    )

    return JsonResponse({'status': 'success'})

@sponsor_required
@require_GET
def global_search(request):
    from beneficiary.models import OrphanForm, SpecialNeedsForm, FamilyForm

    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'items': [], 'total': 0})

    results = []

    # البحث في الثلاثة أنواع
    MAP = [
        (OrphanForm,       'orphan',  _serialize_orphan),
        (SpecialNeedsForm, 'special', _serialize_special),
        (FamilyForm,       'family',  _serialize_family),
    ]

    for Model, tab, serializer in MAP:
        qs = Model.objects.filter(
            sponsor__isnull=True, user__is_approved=True
        ).filter(
            Q(first_name__icontains=q)  | Q(father_name__icontains=q) |
            Q(family_name__icontains=q) | Q(id_number__icontains=q)   |
            Q(form_number__icontains=q) | Q(user__registration_number__icontains=q)
        ).select_related('user')[:20]

        from django.utils import timezone as tz
        week_ago = tz.now() - __import__('datetime').timedelta(days=7)

        for obj in qs:
            item = serializer(obj)
            item['is_new'] = obj.user.date_joined >= week_ago if obj.user.date_joined else False
            results.append(item)

    return JsonResponse({'items': results, 'total': len(results)})