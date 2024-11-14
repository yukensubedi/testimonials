from django.db import models
from django.contrib.auth import get_user_model
from user.models import AuditableModel
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.core.exceptions import ValidationError
import os

User = get_user_model()

class Spaces(AuditableModel):
    user = models.ForeignKey(User, related_name='spaces', on_delete=models.CASCADE)
    spaces_name = models.CharField(max_length=200)
    header_title = models.CharField(max_length=200)
    message = models.TextField()
    spaces_logo = models.ImageField(upload_to='spaces/')
    
    # STAR_RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]
    # star_rating = models.PositiveSmallIntegerField(choices=STAR_RATING_CHOICES, null=True, blank=True)
    star_rating = models.BooleanField(default = False)
    slug = models.SlugField(unique=True, blank=True, max_length=255)

    def __str__(self):
        return self.spaces_name

    def save(self, *args, **kwargs):
        if not self.slug:
            # Generate initial slug from space_name
            self.slug = slugify(self.spaces_name)
            # Ensure the slug is unique
            original_slug = self.slug
            counter = 1
            while Spaces.objects.filter(slug=self.slug).exists():
                self.slug = f'{original_slug}-{counter}'
                counter += 1
        self.spaces_name = self.spaces_name.title()
        super().save(*args, **kwargs)
    
    def generate_space_details_link(self, request):
         return f"{request.build_absolute_uri(reverse('spaces_testimonials_detail', args=[self.slug]))}"

    class Meta:
        ordering = ['-created_at']   


class Question(AuditableModel):
    space = models.ForeignKey(Spaces, related_name='questions', on_delete=models.CASCADE)
    question_text = models.CharField(max_length=500)

    def __str__(self):
        return self.question_text

class Testimonials(AuditableModel):
    spaces = models.ForeignKey(Spaces, related_name='testimonials', on_delete=models.CASCADE)
    testimonial_text = models.TextField()
    sender_name = models.CharField(max_length=200)
    sender_email = models.EmailField( _("email address"))
    STAR_RATING_CHOICES = [(i, f'{i} Stars') for i in range(1, 6)]
    star_rating = models.PositiveSmallIntegerField(choices=STAR_RATING_CHOICES, null=True, blank=True)

    def __str__(self):
        return f'Testimonial by {self.sender_name} for {self.spaces}'

class WallofLove(AuditableModel):
    user = models.ForeignKey(User, related_name='wall_of_love_users', on_delete=models.CASCADE)
    testimonial = models.ForeignKey(Testimonials, related_name='wall_of_love_testimonials', on_delete=models.CASCADE)

    def generate_embed_url(self, request):
        # Get the slug of the space associated with the testimonial
        space_slug = self.testimonial.spaces.slug
        # Build the URL using reverse and request
        return request.build_absolute_uri(reverse('embed_wall_of_love', args=[space_slug]))