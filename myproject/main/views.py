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
                if admin_req:
                    return redirect('/')
                else:
                    return redirect('admin/')
            return func(request)
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
    return render(request, 'inv/orders.html')

@check_login()
def profile(request):
    return render(request, 'inv/profile.html')

@check_login(admin_req=True)
def admin(request):
    context = {}
    context['inventory'] = datahook_lib.fetch_inventory()
    context['users'] = datahook_lib.fetch_all_users('user')
    return render(request, 'inv/admin.html', context=context)

def test(request):
    context = {}
    context = datahook_lib.fetch_inventory()
    print(context)
    return render(request, 'inv/test.html', context=context)

def logout(request):
    datahook_lib.end_session(request.session.session_key, request.META['REMOTE_ADDR'])
    return redirect('/index/')

def create_request(request):
    print(request.POST)
    datahook_lib.create_request('to_pin_element', request.POST['item_id'], int(request.POST['quantity']), request.session.session_key, request.META['REMOTE_ADDR'])
    return redirect('/')

def create_request_view(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        quantity = int(request.POST.get('quantity'))
        
        # Вызов функции из библиотеки datahook_lib
        result = datahook_lib.create_request(
            r_type="to_pin_element",
            eid=item_id,
            amount=quantity,
            session_key=request.session.session_key,
            ip_addr=request.META['REMOTE_ADDR'],
            description=""  # Опционально
        )
        
        if result['error']:
            messages.error(request, f"Ошибка: {result['error']}")
        else:
            messages.success(request, "Заявка отправлена администратору!")
        
        return redirect('main')
    
@check_login(admin_req=True)
def admin(request):
    context = {}
    
    # Получение данных
    context['inventory'] = datahook_lib.fetch_inventory()
    context['users'] = datahook_lib.fetch_all_users('user')
    
    # Получение всех заявок
    requests_data = datahook_lib.fetch_all_requests(r_type="to_pin_element")
    context['requests'] = requests_data['results'] if not requests_data['error'] else []
    
    return render(request, 'inv/admin.html', context=context)

@check_login(admin_req=True)
def approve_request(request, request_id):
    result = datahook_lib.approve_request(request_id=request_id)
    if result['error']:
        messages.error(request, f"Ошибка: {result['error']}")
    else:
        messages.success(request, "Заявка одобрена!")
    return redirect('admin')

@check_login(admin_req=True)
def decline_request(request, request_id):
    result = datahook_lib.decline_request(request_id=request_id)
    if result['error']:
        messages.error(request, f"Ошибка: {result['error']}")
    else:
        messages.success(request, "Заявка отклонена!")
    return redirect('admin')