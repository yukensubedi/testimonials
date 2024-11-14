from django.contrib import admin
from .models import Spaces, Question, Testimonials, WallofLove

# Register your models here.
admin.site.register(Testimonials)
admin.site.register(WallofLove)


from django.contrib import admin
from .models import Spaces, Question

class SpacesAdmin(admin.ModelAdmin):
    list_display = ('spaces_name', 'user', 'header_title', 'star_rating',  'created_at')
    search_fields = ('spaces_name', 'user__email')  # search by space name, slug, and user email
    list_filter = ('star_rating', 'created_at')  # filter by star rating and created_at
    readonly_fields = ('created_at', 'updated_at')  # fields that should be readonly
    ordering = ('-created_at',)  # order by creation date
    fieldsets = (
        (None, {
            'fields': ('spaces_name', 'header_title', 'message', 'spaces_logo', 'star_rating',  'user')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
        }),
    )
    
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'space', 'created_at')
    search_fields = ('question_text', 'space__spaces_name')  # search by question text and associated space name
    list_filter = ('created_at', 'space__spaces_name')  # filter by creation date and space name
    ordering = ('-created_at',)  # order by creation date

# Register the models with their corresponding admin classes
admin.site.register(Spaces, SpacesAdmin)
admin.site.register(Question, QuestionAdmin)
