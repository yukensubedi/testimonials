from django import forms
from . models import Spaces, Question, Testimonials
from django.forms import inlineformset_factory
from django.forms import BaseInlineFormSet
from django.core.exceptions import ValidationError


class SpacesForm(forms.ModelForm):
    class Meta:
        model = Spaces
        fields = ['spaces_name', 'header_title', 'message', 'spaces_logo', 'star_rating']
        widgets = {
            'spaces_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter space name'}),
            'header_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter header title'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter your message', 'rows': 4}),
            'spaces_logo': forms.FileInput(attrs={'class': 'form-control'}),
             'star_rating': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    def clean(self):
        cleaned_data = super().clean()
        if spaces_logo:= cleaned_data.get('spaces_logo'):

            if not spaces_logo.name.endswith(('.png', '.jpg', '.jpeg')):
                raise forms.ValidationError("Only image files (PNG, JPG, JPEG) are allowed for spaces logo.")
            
            max_size = 5 * 1024 * 1024  # 5 MB in bytes
            if spaces_logo.size > max_size:
                raise forms.ValidationError("The image file size should not exceed 5 MB.")
        
        return cleaned_data


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['question_text']
        widgets = {
            'question_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter question'}),
        }
  

QuestionFormSet = inlineformset_factory(Spaces, Question, form=QuestionForm, extra=1, fields=['question_text'])


class TestimonialForm(forms.ModelForm):
    star_rating = forms.ChoiceField(
        choices=Testimonials.STAR_RATING_CHOICES,
        required=False, 
        widget=forms.RadioSelect
    )
    class Meta:
        model = Testimonials
        fields = ['sender_name', 'sender_email', 'testimonial_text', 'star_rating']
        
        widgets = {
            'sender_name': forms.TextInput(attrs={'class': 'form-control','placeholder': 'Your name'}),
            'sender_email': forms.EmailInput(attrs={'class': 'form-control','placeholder': 'Your email'}),
            'testimonial_text': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Your testimonial',  'rows': 3, 'cols': 40})
        }
    def __init__(self, *args, **kwargs):
        allow_star_rating = kwargs.pop('allow_star_rating', False)
        super().__init__(*args, **kwargs)
        if not allow_star_rating:
            self.fields.pop('star_rating')


class SampleForm(forms.Form):
    name = forms.CharField(max_length=50, required=True)
    email = forms.EmailField(required=True)
    age = forms.IntegerField(min_value=18, required=True)
    bio = forms.CharField(widget=forms.Textarea, required=False)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and "test.com" not in email:
            raise forms.ValidationError("Email domain must be 'test.com'.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        age = cleaned_data.get("age")
        
        if name and age and age < 25 and name.lower() == "admin":
            raise forms.ValidationError("Admin must be at least 25 years old.")
        return cleaned_data