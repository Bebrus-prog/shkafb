from django.shortcuts import render, redirect
from .datahook import datahook_lib
from django.http import HttpResponseRedirect

def main(request):
    session = datahook_lib.session_check(request.session.session_key, request.META['REMOTE_ADDR'])
    if session['error'] == 'no_result':
        return redirect('/index') 
    else:
        ...
    print(session)
    return render(request, 'inv/main.html')

def index(request):
    if not request.session.session_key:
            request.session.create()
    if request.POST:
        postdata = request.POST
        login = postdata['login']
        password = postdata['password']
        funcreturn = datahook_lib.fetch_login(login, password, request.session.session_key, request.META['REMOTE_ADDR'])
        print(f'funcreturn = {funcreturn}')
        if not funcreturn['error']:
            return redirect('/')
    return render(request, 'inv/index.html')
#TODO: login verification everywhere

def orders(request):
    return render(request, 'inv/orders.html')

def profile(request):
    return render(request, 'inv/profile.html')
