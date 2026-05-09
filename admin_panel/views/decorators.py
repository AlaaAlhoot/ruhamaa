from functools import wraps
from django.shortcuts import redirect, render


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/login/')
        if request.user.user_type != 'admin':
            return redirect('/login/')
        return view_func(request, *args, **kwargs)
    return wrapper

def settings_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('admin_login')
        if request.user.user_type != 'admin':
            return redirect('admin_login')
        if not request.user.is_superuser and not getattr(request.user,'can_access_settings',False):
            return render(request,'admin_panel/403.html',status=403)
        return view_func(request, *args, **kwargs)
    return wrapper