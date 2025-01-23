from django import forms
from django.contrib.auth.models import User

class LoginForm:
    login = forms.CharField(max_length=30)
    password = forms.CharField(max_length=128)