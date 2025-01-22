from django.shortcuts import render, redirect
from .datahook import datahook_lib
from django.http import HttpResponseRedirect

def check_login(func):
    def wrapper(request):
        session = datahook_lib.session_check(request.session.session_key, request.META['REMOTE_ADDR'])
        if session['error'] == 'no_result':
            return redirect('/index') 
        return func(request)
    return wrapper

@check_login
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

@check_login
def orders(request):
    return render(request, 'inv/orders.html')

@check_login
def profile(request):
    return render(request, 'inv/profile.html')
