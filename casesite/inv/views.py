from django.shortcuts import render

def main(request):
    return render(request, 'inv/main.html')

def index(request):
    return render(request, 'inv/index.html')

def orders(request):
    return render(request, 'inv/orders.html')

def profile(request):
    return render(request, 'inv/profile.html')
