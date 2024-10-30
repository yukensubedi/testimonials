from django.contrib import admin
from .models import Spaces, Question, Testimonials, WallofLove

# Register your models here.
admin.site.register(Question)
admin.site.register(Testimonials)
admin.site.register(Spaces)
admin.site.register(WallofLove)