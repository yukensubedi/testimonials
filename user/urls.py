from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('signin', views.SignInView.as_view(), name='sign_in'),
    path('logout/', views.LogoutView.as_view(), name='logout'), 
    # path('auth-receiver', views.auth_receiver, name='auth_receiver'),
    path('auth-receiver', views.AuthGoogleView.as_view(), name='auth_receiver'),

]
