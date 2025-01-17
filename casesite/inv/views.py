from django.shortcuts import render, redirect
from .datahook import datahook_lib
from django.http import HttpResponseRedirect

def main(request):
    return render(request, 'inv/main.html')

def index(request):
    if request.POST:
        data = request.POST
        login = data['login']
        password = data['password']
        datahook_lib.fetch_login(login, password, request.session.session_key, request.META.REMOTE_ADDR) 
        return redirect()
    return render(request, 'inv/index.html')

def orders(request):
    return render(request, 'inv/orders.html')

def profile(request):
    return render(request, 'inv/profile.html')
