from django.shortcuts import render, redirect
from .datahook import datahook_lib
from django.http import HttpResponseRedirect
from django.contrib import messages

def check_login(admin_req=False):
    def decorator(func):
        def wrapper(request):
            session = datahook_lib.session_check(request.session.session_key, request.META['REMOTE_ADDR'], admin_needed=admin_req)
            if session['error'] == 'no_result':
                return redirect('/index') 
            if session['error'] == 'no_permission':
                # messages.warning(request, 'У вас нет доступа к этой странице')
                if admin_req:
                    return redirect('/')
                else:
                    return redirect('admin/')
            return func(request)
        return wrapper
    return decorator

@check_login()
def main(request):
    return render(request, 'inv/main.html')

def index(request):
    if not request.session.session_key:
            request.session.create()
    if request.POST:
        postdata = request.POST
        login = postdata['login']
        password = postdata['password']
        funcreturn = datahook_lib.fetch_login(login, password, request.session.session_key, request.META['REMOTE_ADDR'])
        if not funcreturn['error']:
            return redirect('/')
    return render(request, 'inv/index.html')

@check_login()
def orders(request):
    return render(request, 'inv/orders.html')

@check_login()
def profile(request):
    return render(request, 'inv/profile.html')

@check_login(admin_req=True)
def admin(request):
    return render(request, 'inv/admin.html')

def test(request):
    context = {}
    context = datahook_lib.fetch_inventory()
    print(context)
    return render(request, 'inv/test.html', context=context)

def logout(request):
    datahook_lib.end_session(request.session.session_key, request.META['REMOTE_ADDR'])
    return redirect('/index/')
