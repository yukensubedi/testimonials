from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('signin', views.SignInView.as_view(), name='sign_in'),
    path('logout/', views.LogoutView.as_view(), name='logout'), 

    path('auth/google/', views.google_login, name='google_login'),
    path('auth/google/callback/', views.google_callback, name='google_callback'),

]
