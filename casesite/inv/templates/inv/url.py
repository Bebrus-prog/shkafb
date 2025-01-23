from django.urls import path
from django.contrib.auth.views import LogoutView

urlpatterns = [
    # ... другие маршруты ...
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
]