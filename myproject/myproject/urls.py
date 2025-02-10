"""
URL configuration for case project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from main import views

urlpatterns = [
    path('', views.main, name='main'),
    path('index/', views.index, name='index'),
    path('orders/', views.orders, name='orders'),
    path('profile/', views.profile, name='profile'),
    path('admin/', views.admin, name='admin'),
    path('test/', views.test, name='test'),
    path('logout/', views.logout, name='logout'),
    path('order/', views.create_request, name='order'),
    path('reject/', views.reject_request, name='reject'),
    path('approve/', views.approve_request, name='approve'),
    path('return/', views.return_item, name='return_item'),
    path('cancel/', views.cancel_request, name='cancel_request'),
    path('edit/', views.edit_item, name='edit_item'),
    path('admin/add_item', views.add_item, name='add_item'),
    path('delete_i/', views.delete_item, name='delete_item'),
    path('add_p/', views.add_plan, name='add_plan'),
    path('delete_p/', views.delete_plan, name='delete_plan'),
    path('add_u/', views.add_user, name='add_user'),
    path('assign_a/', views.assign_admin, name='assign_admin'),
]
