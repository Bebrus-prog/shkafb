from django.shortcuts import render, redirect
from .datahook import datahook_lib
from django.http import HttpResponseRedirect
from django.contrib import messages


def check_login(admin_req=False):
    def decorator(func):
        def wrapper(*args, **kwargs):
            session = datahook_lib.session_check(args[0].session.session_key, args[0].META['REMOTE_ADDR'], admin_needed=admin_req)
            if session['error'] == 'no_result':
                return redirect('/index') 
            if session['error'] == 'no_permission':
                if admin_req:
                    return redirect('/')
                else:
                    return redirect('admin/')
            return func(*args, **kwargs)
        return wrapper
    return decorator


@check_login()
def main(request):
    context = {}
    context['inventory'] = datahook_lib.fetch_inventory()
    return render(request, 'inv/main.html', context=context)


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
    context = {}
    context['sentreqs'] = datahook_lib.fetch_sent_requests(request.session.session_key, request.META['REMOTE_ADDR'])
    return render(request, 'inv/orders.html', context=context)


@check_login()
def profile(request):
    context = {}
    context['bels'] = datahook_lib.fetch_my_belongings(request.session.session_key, request.META['REMOTE_ADDR'])
    context['reqs'] = datahook_lib.fetch_sent_requests(request.session.session_key, request.META['REMOTE_ADDR'])
    return render(request, 'inv/profile.html', context=context)


@check_login(admin_req=True)
def admin(request):
    context = {}
    context['inventory'] = datahook_lib.fetch_inventory()
    context['users'] = datahook_lib.fetch_all_users('user')
    context['orders'] = datahook_lib.fetch_all_requests('to_pin_element')
    context['plan'] = datahook_lib.fetch_plan()
    context['report'] = datahook_lib.create_report()
    return render(request, 'inv/admin.html', context=context)


def test(request):
    context = {}
    context = datahook_lib.fetch_inventory()
    print(context)
    return render(request, 'inv/test.html', context=context)


def logout(request):
    datahook_lib.end_session(request.session.session_key, request.META['REMOTE_ADDR'])
    return redirect('/index/')


@check_login()
def create_request(request):
    datahook_lib.create_request('to_pin_element', request.POST['item_id'], int(request.POST['quantity']), request.session.session_key, request.META['REMOTE_ADDR'])
    return redirect('/')


@check_login(True)
def approve_request(request):
    datahook_lib.approve_request(request.POST['id'])
    return redirect('/admin/')


@check_login(True)
def reject_request(request):
    datahook_lib.decline_request(request.POST['id'])
    return redirect('/admin/')


@check_login()
def return_item(request):
    datahook_lib.return_my_belonging(request.POST['id'], request.session.session_key, request.META['REMOTE_ADDR'])
    return redirect('/profile/')


def cancel_request(request):
    datahook_lib.cancel_request(request.POST['id'], request.session.session_key, request.META['REMOTE_ADDR'])
    return redirect('/profile/')


@check_login(True)
def edit_item(request):
    data = request.POST
    datahook_lib.edit_inventory_object(data['id'], data['name'], int(data['amount']), int(data['status']), request.session.session_key, request.META['REMOTE_ADDR'])
    return redirect('/admin/')


@check_login(True)
def add_item(request):
    data = request.POST
    datahook_lib.add_to_inventory(data['name'], int(data['amount']), int(data['status']), request.session.session_key, request.META['REMOTE_ADDR'])
    return redirect('/admin/')


@check_login(True)
def delete_item(request):
    datahook_lib.remove_from_inventory(request.POST['id'], request.session.session_key, request.META['REMOTE_ADDR'])
    return redirect('/admin/')


@check_login(True)
def add_plan(request):
    data = request.POST
    datahook_lib.add_to_plan(data['name'], int(data['price']), int(data['amount']), data['supplier'])
    return redirect('/admin/')


@check_login(True)
def delete_plan(request):
    datahook_lib.remove_from_plan(int(request.POST['id']))
    return redirect('/admin/')


def add_user(request):
    data = request.POST
    datahook_lib.register_user(data['username'], data['firstname'], data['password'], data['secondname'])
    return redirect('/admin/')


@check_login(True)
def assign_admin(request):
    datahook_lib.assign_administrator(request.POST['username'])
    return redirect('/admin/')

def register_page(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, 'Пароли не совпадают')
            return redirect('register')

        # Регистрация через datahook
        result = datahook_lib.register_user(username, password)
        
        if result.get('error'):
            error = result['error']
            if error == 'user_existing':
                messages.error(request, 'Логин уже занят')
            elif error in ['length', 'symbol']:
                messages.error(request, 'Некорректный формат логина')
            else:
                messages.error(request, 'Ошибка регистрации')
            return redirect('register')
        else:
            messages.success(request, 'Регистрация успешна! Войдите в систему')
            return redirect('index')
    
    return render(request, 'inv/register.html')