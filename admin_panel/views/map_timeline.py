"""
map_timeline.py — فيوز الخريطة الجغرافية والتايم لاين
"""

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import date

from core.models import CustomUser, Payment, Aid, ActivityLog
from admin_panel.views.decorators import admin_required


# ══════════════════════════════════════════════
# إحداثيات المدن الفلسطينية
# ══════════════════════════════════════════════
PALESTINE_CITIES = {
    'غزة':           {'lat': 31.5017, 'lng': 34.4668},
    'مدينة غزة':     {'lat': 31.5017, 'lng': 34.4668},
    'رفح':           {'lat': 31.2965, 'lng': 34.2590},
    'خان يونس':      {'lat': 31.3451, 'lng': 34.3062},
    'دير البلح':     {'lat': 31.4175, 'lng': 34.3520},
    'بيت لاهيا':     {'lat': 31.5530, 'lng': 34.4916},
    'بيت حانون':     {'lat': 31.5369, 'lng': 34.5319},
    'جباليا':        {'lat': 31.5293, 'lng': 34.4835},
    'الشجاعية':      {'lat': 31.5075, 'lng': 34.4891},
    'الزيتون':       {'lat': 31.5000, 'lng': 34.4700},
    'النصيرات':      {'lat': 31.4390, 'lng': 34.3828},
    'البريج':        {'lat': 31.4546, 'lng': 34.3974},
    'المغازي':       {'lat': 31.4270, 'lng': 34.3924},
    'الشابورة':      {'lat': 31.2987, 'lng': 34.2506},
    'تل السلطان':    {'lat': 31.2820, 'lng': 34.2476},
}

# ══════════════════════════════════════════════
# إحداثيات الدول
# ══════════════════════════════════════════════
COUNTRY_COORDS = {
    'فلسطين':          {'lat': 31.9,    'lng': 35.2},
    'الأردن':          {'lat': 31.963,  'lng': 35.930},
    'السعودية':        {'lat': 23.885,  'lng': 45.079},
    'الإمارات':        {'lat': 23.424,  'lng': 53.848},
    'الكويت':          {'lat': 29.378,  'lng': 47.990},
    'قطر':             {'lat': 25.354,  'lng': 51.184},
    'البحرين':         {'lat': 26.067,  'lng': 50.558},
    'عُمان':           {'lat': 21.512,  'lng': 55.923},
    'مصر':             {'lat': 26.820,  'lng': 30.802},
    'تركيا':           {'lat': 38.964,  'lng': 35.243},
    'ألمانيا':         {'lat': 51.166,  'lng': 10.452},
    'المملكة المتحدة': {'lat': 55.378,  'lng': -3.436},
    'الولايات المتحدة':{'lat': 37.090,  'lng': -95.713},
    'كندا':            {'lat': 56.130,  'lng': -106.347},
    'أستراليا':        {'lat': -25.274, 'lng': 133.775},
    'ماليزيا':         {'lat': 4.211,   'lng': 101.976},
    'إندونيسيا':       {'lat': -0.790,  'lng': 113.921},
    'فرنسا':           {'lat': 46.228,  'lng': 2.214},
    'هولندا':          {'lat': 52.133,  'lng': 5.291},
    'السويد':          {'lat': 60.128,  'lng': 18.644},
    'النرويج':         {'lat': 60.472,  'lng': 8.469},
    'الدنمارك':        {'lat': 56.263,  'lng': 9.502},
    'بلجيكا':          {'lat': 50.504,  'lng': 4.470},
    'سويسرا':          {'lat': 46.818,  'lng': 8.228},
    'إيطاليا':         {'lat': 41.872,  'lng': 12.567},
    'إسبانيا':         {'lat': 40.164,  'lng': -3.702},
    'اليونان':         {'lat': 39.074,  'lng': 21.824},
    'النمسا':          {'lat': 47.516,  'lng': 14.551},
    'بولندا':          {'lat': 51.919,  'lng': 19.145},
    'رومانيا':         {'lat': 45.943,  'lng': 24.967},
    'الجزائر':         {'lat': 28.034,  'lng': 1.660},
    'المغرب':          {'lat': 31.792,  'lng': -7.093},
    'تونس':            {'lat': 33.887,  'lng': 9.537},
    'ليبيا':           {'lat': 26.335,  'lng': 17.228},
    'السودان':         {'lat': 12.863,  'lng': 30.218},
    'العراق':          {'lat': 33.224,  'lng': 43.679},
    'سوريا':           {'lat': 34.802,  'lng': 38.997},
    'لبنان':           {'lat': 33.855,  'lng': 35.862},
    'اليمن':           {'lat': 15.553,  'lng': 48.516},
    'باكستان':         {'lat': 30.376,  'lng': 69.346},
    'الهند':           {'lat': 20.594,  'lng': 78.963},
    'الصين':           {'lat': 35.861,  'lng': 104.196},
    'اليابان':         {'lat': 36.204,  'lng': 138.253},
    'كوريا الجنوبية':  {'lat': 35.908,  'lng': 127.767},
}


def _get_city_coords(city):
    """جلب إحداثيات مدينة مع fallback"""
    if not city:
        return {'lat': 31.5017 + (hash('') % 100) * 0.003,
                'lng': 34.4668 + (hash('') % 50) * 0.003}
    coords = PALESTINE_CITIES.get(city)
    if coords:
        return coords
    for k, v in PALESTINE_CITIES.items():
        if k in city or city in k:
            return v
    h = hash(city) % 1000
    return {'lat': 31.4 + (h % 30) * 0.01, 'lng': 34.3 + (h % 20) * 0.01}


def _get_country_coords(country):
    """جلب إحداثيات دولة"""
    if not country:
        return {'lat': 31.9, 'lng': 35.2}
    coords = COUNTRY_COORDS.get(country)
    if coords:
        return coords
    h = hash(country) % 1000
    return {'lat': 25.0 + (h % 30) * 0.5, 'lng': 45.0 + (h % 20) * 0.5}


# ══════════════════════════════════════════════
# الصفحة الرئيسية
# ══════════════════════════════════════════════
@admin_required
@require_GET
def page(request):
    return render(request, 'admin_panel/map_timeline.html')


# ══════════════════════════════════════════════
# بيانات الخريطة
# ══════════════════════════════════════════════
@admin_required
@require_GET
def map_data(request):
    from beneficiary.models import OrphanForm, FamilyForm, SpecialNeedsForm
    from sponsor.models import SponsorProfile

    TYPE_CONFIG = {
        'orphan':  (OrphanForm,       'يتيم',         '#22c55e'),
        'family':  (FamilyForm,        'أسرة',         '#3b82f6'),
        'special': (SpecialNeedsForm,  'ذوو احتياجات', '#f59e0b'),
    }

    # ── المستفيدون ──
    bene_points = []
    for btype, (Model, label, color) in TYPE_CONFIG.items():
        try:
            forms = Model.objects.select_related('user', 'sponsor', 'sponsor__user').all()
            for f in forms:
                try:
                    city   = getattr(f, 'current_city', '') or ''
                    coords = _get_city_coords(city)
                    sponsor_name = '—'
                    if hasattr(f, 'sponsor') and f.sponsor and hasattr(f.sponsor, 'user'):
                        sponsor_name = f.sponsor.user.get_full_name()
                    bene_points.append({
                        'id':      str(f.user.pk),
                        'name':    f.user.get_full_name(),
                        'type':    btype,
                        'label':   label,
                        'color':   color,
                        'city':    city or 'غير محدد',
                        'status':  f.status,
                        'sponsor': sponsor_name,
                        'lat':     coords['lat'],
                        'lng':     coords['lng'],
                    })
                except Exception:
                    continue
        except Exception:
            continue

    # ── الكفلاء ──
    sponsor_points = []
    try:
        sponsors = SponsorProfile.objects.select_related('user').all()
        for sp in sponsors:
            try:
                from beneficiary.models import OrphanForm as OF, FamilyForm as FF, SpecialNeedsForm as SF
                country = sp.country or ''
                coords  = _get_country_coords(country)
                benes_c = (
                    OF.objects.filter(sponsor=sp).count() +
                    FF.objects.filter(sponsor=sp).count() +
                    SF.objects.filter(sponsor=sp).count()
                )
                total_paid = Payment.objects.filter(
                    sponsor=sp.user
                ).aggregate(s=Sum('amount_ils'))['s'] or 0

                sponsor_points.append({
                    'id':         str(sp.user.pk),
                    'name':       sp.user.get_full_name(),
                    'country':    country or 'غير محدد',
                    'city':       sp.city or '',
                    'benes':      benes_c,
                    'total_paid': str(round(total_paid, 2)),
                    'lat':        coords['lat'],
                    'lng':        coords['lng'],
                })
            except Exception:
                continue
    except Exception:
        pass

    # ── إحصائيات ──
    from sponsor.models import SponsorProfile as SP
    sponsor_countries = SP.objects.exclude(
        country=''
    ).values('country').annotate(c=Count('id')).order_by('-c')

    total_benes     = len(bene_points)
    sponsored_benes = len([p for p in bene_points if p['sponsor'] != '—'])
    top_country     = sponsor_countries.first()

    orphan_count  = len([p for p in bene_points if p['type'] == 'orphan'])
    family_count  = len([p for p in bene_points if p['type'] == 'family'])
    special_count = len([p for p in bene_points if p['type'] == 'special'])

    return JsonResponse({
        'benes':    bene_points,
        'sponsors': sponsor_points,
        'stats': {
            'total_benes':       total_benes,
            'sponsored_benes':   sponsored_benes,
            'unsponsored_benes': total_benes - sponsored_benes,
            'coverage_pct':      round(sponsored_benes / total_benes * 100, 1) if total_benes else 0,
            'top_country':       top_country['country'] if top_country else '—',
            'total_countries':   sponsor_countries.count(),
            'orphan_count':      orphan_count,
            'family_count':      family_count,
            'special_count':     special_count,
            'sponsor_count':     len(sponsor_points),
        },
        'charts': {
            'monthly_registrations': _monthly_registrations(),
            'monthly_payments':      _monthly_payments(),
            'country_distribution':  [
                {'country': x['country'], 'count': x['c']}
                for x in sponsor_countries[:10]
            ],
        },
    })


# ══════════════════════════════════════════════
# بيانات التايم لاين
# ══════════════════════════════════════════════
@admin_required
@require_GET
def timeline_data(request):
    mode    = request.GET.get('mode',    'individual')
    user_id = request.GET.get('user_id', '').strip()
    btype   = request.GET.get('type',    'orphan')

    from beneficiary.models import OrphanForm, FamilyForm, SpecialNeedsForm

    STATUS_MAP = {'paid': 'مدفوعة', 'pending': 'معلّقة', 'late': 'متأخرة'}
    AID_TYPES  = {
        'food': 'غذائية', 'medical': 'طبية', 'financial': 'مالية',
        'clothing': 'ملابس', 'furniture': 'أثاث', 'education': 'تعليمية', 'other': 'أخرى',
    }
    MODEL_MAP = {
        'orphan':  OrphanForm,
        'family':  FamilyForm,
        'special': SpecialNeedsForm,
    }

    def _user_events(user):
        """جمع أحداث مستفيد واحد"""
        events = []

        # التسجيل
        events.append({
            'date':  user.date_joined.date().isoformat(),
            'type':  'register',
            'icon':  '📝',
            'color': '#7c3aed',
            'title': 'تسجيل في المنصة',
            'desc':  f'تم تسجيل {user.get_full_name()} في المنصة',
            'user':  user.get_full_name(),
            'uid':   str(user.pk),
        })

        # سجل النشاط
        try:
            logs = ActivityLog.objects.filter(
                Q(user=user) | Q(target_id=str(user.pk), target_model='CustomUser')
            ).order_by('created_at')
            for log in logs:
                if 'قبول' in log.description or 'تدقيق' in log.description:
                    icon, color = '✅', '#1a7a4a'
                elif 'كافل' in log.description:
                    icon, color = '🤝', '#1a7a4a'
                elif 'تعطيل' in log.description:
                    icon, color = '🔴', '#c53030'
                elif 'تفعيل' in log.description:
                    icon, color = '✅', '#1a7a4a'
                else:
                    icon, color = '📌', '#6b7280'
                events.append({
                    'date':  log.created_at.date().isoformat(),
                    'type':  'log',
                    'icon':  icon,
                    'color': color,
                    'title': log.description,
                    'desc':  f'بواسطة: {log.user.get_full_name() if log.user else "النظام"}',
                    'user':  user.get_full_name(),
                    'uid':   str(user.pk),
                })
        except Exception:
            pass

        # الدفعات
        try:
            for p in Payment.objects.filter(beneficiary=user).order_by('date'):
                events.append({
                    'date':  str(p.date),
                    'type':  'payment',
                    'icon':  '💰',
                    'color': '#1a7a4a',
                    'title': f'دفعة {p.amount_ils}₪',
                    'desc':  f'{STATUS_MAP.get(p.status, p.status)} — {p.note or ""}',
                    'user':  user.get_full_name(),
                    'uid':   str(user.pk),
                })
        except Exception:
            pass

        # المساعدات
        try:
            for a in Aid.objects.filter(beneficiary=user).order_by('date'):
                events.append({
                    'date':  str(a.date),
                    'type':  'aid',
                    'icon':  '🎁',
                    'color': '#b45309',
                    'title': a.name,
                    'desc':  f'{AID_TYPES.get(a.aid_type, a.aid_type)} — {a.provider}',
                    'user':  user.get_full_name(),
                    'uid':   str(user.pk),
                })
        except Exception:
            pass

        # الملاحظات
        try:
            from core.models import UserNote
            for n in UserNote.objects.filter(user=user).order_by('created_at'):
                events.append({
                    'date':  n.created_at.date().isoformat(),
                    'type':  'note',
                    'icon':  '📝',
                    'color': '#6b7280',
                    'title': 'ملاحظة',
                    'desc':  (n.note[:80] + '...') if len(n.note) > 80 else n.note,
                    'user':  user.get_full_name(),
                    'uid':   str(user.pk),
                })
        except Exception:
            pass

        return sorted(events, key=lambda x: x['date'])

    # ── وضع فردي ──
    if mode == 'individual':
        if not user_id:
            return JsonResponse({'events': [], 'mode': 'individual'})
        try:
            user   = CustomUser.objects.get(pk=user_id)
            events = _user_events(user)
            return JsonResponse({
                'mode':   'individual',
                'user':   user.get_full_name(),
                'events': events,
            })
        except CustomUser.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'المستخدم غير موجود'})

    # ── وضع حسب النوع ──
    elif mode == 'type':
        Model = MODEL_MAP.get(btype)
        if not Model:
            return JsonResponse({'events': [], 'mode': 'type'})
        all_events = []
        try:
            forms = Model.objects.select_related('user').all()[:50]
            for f in forms:
                try:
                    all_events.extend(_user_events(f.user))
                except Exception:
                    continue
        except Exception:
            pass
        return JsonResponse({
            'mode':   'type',
            'type':   btype,
            'events': sorted(all_events, key=lambda x: x['date']),
        })

    # ── وضع جماعي ──
    elif mode == 'all':
        all_events = []
        try:
            users = CustomUser.objects.filter(
                user_type__in=['orphan', 'family', 'special']
            ).order_by('date_joined')[:30]
            for user in users:
                try:
                    all_events.extend(_user_events(user))
                except Exception:
                    continue
        except Exception:
            pass
        return JsonResponse({
            'mode':   'all',
            'events': sorted(all_events, key=lambda x: x['date']),
        })

    return JsonResponse({'events': [], 'mode': mode})


# ══════════════════════════════════════════════
# بحث المستفيدين للقائمة
# ══════════════════════════════════════════════
@admin_required
@require_GET
def search_beneficiaries(request):
    q = request.GET.get('q', '').strip()

    qs = CustomUser.objects.filter(
        user_type__in=['orphan', 'family', 'special', 'sponsor'],
    )

    if q and len(q) >= 2:
        qs = qs.filter(
            Q(first_name__icontains=q)   |
            Q(father_name__icontains=q)  |
            Q(family_name__icontains=q)  |
            Q(registration_number__icontains=q) |
            Q(id_number__icontains=q)
        )

    qs = qs.order_by('user_type', 'first_name')[:200]

    TYPE_LABELS = {
        'orphan':  'يتيم',
        'family':  'أسرة',
        'special': 'ذوو احتياجات',
        'sponsor': 'كافل',
    }

    return JsonResponse({
        'results': [{
            'id':   str(u.pk),
            'name': u.get_full_name(),
            'type': u.user_type,
            'reg':  u.registration_number or '',
        } for u in qs]
    })


# ══════════════════════════════════════════════
# مساعدات
# ══════════════════════════════════════════════
def _monthly_registrations():
    """التسجيلات الشهرية — آخر 12 شهر"""
    try:
        from dateutil.relativedelta import relativedelta
        today  = date.today()
        result = []
        for i in range(11, -1, -1):
            m     = today - relativedelta(months=i)
            count = CustomUser.objects.filter(
                user_type__in=['orphan', 'family', 'special'],
                date_joined__year=m.year,
                date_joined__month=m.month,
            ).count()
            result.append({'month': f'{m.year}/{m.month:02d}', 'count': count})
        return result
    except Exception:
        return []


def _monthly_payments():
    """المدفوعات الشهرية — آخر 12 شهر"""
    try:
        from dateutil.relativedelta import relativedelta
        today  = date.today()
        result = []
        for i in range(11, -1, -1):
            m     = today - relativedelta(months=i)
            total = Payment.objects.filter(
                date__year=m.year,
                date__month=m.month,
            ).aggregate(s=Sum('amount_ils'))['s'] or 0
            result.append({'month': f'{m.year}/{m.month:02d}', 'total': float(round(total, 2))})
        return result
    except Exception:
        return []
