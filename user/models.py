from django.db import models
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from . managers import CustomUserManager
from django.utils.translation import gettext_lazy as _
from django.conf  import settings
from datetime import datetime, timezone


SIGNUP_METHODS = (
        ('GOOGLE', 'GOOGLE'),
        ('FORM', 'FORM'),
        
    )
class AuditableModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class User(AbstractBaseUser, PermissionsMixin, AuditableModel):
    email = models.EmailField(
        _("email address"), unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)  
   
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False) 
    is_verified = models.BooleanField(default=False)

    signup_method = models.CharField(choices=SIGNUP_METHODS, max_length=20, default='FORM')

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def save_last_login(self) -> None:
        self.last_login = datetime.now()
        self.save()
    
    

