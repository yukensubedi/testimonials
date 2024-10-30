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

