from django.db.models.query import QuerySet
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.list import ListView
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib import messages

from django.urls import reverse_lazy, reverse
from django.db.models import Avg, Count
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden, HttpResponse, JsonResponse
from django.core.exceptions import ValidationError

from .models import Spaces, Question, Testimonials, WallofLove
from .forms import SpacesForm, QuestionFormSet, TestimonialForm, SampleForm
from django_filters.views import FilterView
from .filters import SpacesFilter
from .tasks import send_email
import json


def test_view(request):
    subject = "Welcome to Our Platform"
    template_path = "emails/test"  # Path to your email template
    receiver = ["rukn500@gmail.com"]
    merge_data = {
            "user_name": request.user.first_name, 
            "welcome_message": "Thank you for joining us!"
        }

        # Send email asynchronously
    try:
            send_email.delay(subject, template_path, receiver, merge_data)
            messages.success(request, "Email has been sent successfully!")
    except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
    return HttpResponse('Emnailsent')

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'app/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user  
        spaces =  Spaces.objects.filter(user=user).prefetch_related('testimonials') 
        context['spaces'] = spaces
        context['spaces_count'] = context['spaces'].count()
        context['recent_testimonials'] = Testimonials.objects.filter(spaces__user=user).order_by('-created_at')[:5]

        today = timezone.now().date()
        context['recent_testimonials'] = Testimonials.objects.filter(spaces__user=user).order_by('-created_at')[:5]
        context['testimonial_count'] = Testimonials.objects.filter(spaces__user=user).count()

        for space in spaces:
            space.generated_link = space.generate_space_details_link(self.request)
            print(space.generated_link)


        return context



class SpacesCreateView(LoginRequiredMixin, CreateView):
    """
    View to create a Spaces with questions 
    """
    model = Spaces
    form_class = SpacesForm
    template_name = 'app/create_space.html'
    success_url = reverse_lazy('create_spaces')   
    max_questions = 2

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
       
        

        if self.request.POST:
            context['formset'] = QuestionFormSet(self.request.POST, self.request.FILES)
        else:
            context['formset'] = QuestionFormSet()
        context['max_questions'] = self.max_questions
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
       
       
        if len(formset) > self.max_questions:
            messages.warning(self.request, f"You can only add up to {self.max_questions} questions.")
            return self.form_invalid(form)
        
        if not formset.is_valid():
            messages.warning(self.request, "Please correct the errors in the questions.")
            return self.form_invalid(form)

        
        has_valid_question = any(
            question_form.cleaned_data and not question_form.cleaned_data.get('DELETE', False)
            for question_form in formset
        )

        if not has_valid_question:
            form.add_error(None, "Please add at least one question.")
            return self.form_invalid(form)

        try:
            if form.is_valid() and formset.is_valid():
                space = form.save(commit=False)
                space.user = self.request.user
                space.full_clean()  
                space.save()
                
                formset.instance = space  
                formset.save()
                messages.success(self.request, "Spaces with questions created successfully")
                return redirect(self.success_url)
        except ValidationError as e:
            for field, errors in e.message_dict.items():
                for error in errors:
                    form.add_error(field, error)
        return self.form_invalid(form)
    
class TestimonialCollectView(DetailView):

    """
    View to show the details of the spaces to collect testimonials   
    """
    model = Spaces
    template_name = 'app/spaces_testimonial_collect.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        space = self.object
        
        # Fetch all questions related to the space
        context['questions'] = space.questions.all()
        context['testimonials'] = space.testimonials.all()
        context['form'] = TestimonialForm(allow_star_rating=space.star_rating)
        return context
    

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()   
        form = TestimonialForm(request.POST, allow_star_rating=self.object.star_rating)
        
        if form.is_valid():
            testimonial = form.save(commit=False)
            testimonial.spaces = self.object  
            testimonial.save()  


            space_owner_subject = f"New Testimonial Received for {self.object.spaces_name}"
            space_owner_template = 'emails/testimonial_received'
            space_owner_receiver = [self.object.user.email]  # Assuming space owner is self.object.user
            space_owner_merge_data = {
                'space_name': self.object.spaces_name,
                'space_owner_name': self.object.user.get_full_name(),
                'testimonial_text': testimonial.testimonial_text,
                'user_name': testimonial.sender_name,
                'user_email': testimonial.sender_email,
                'url' : self.request.build_absolute_uri(reverse('spaces_detail', args=[self.object.slug]))
            }

            # Prepare data for the email to the sender (thank you message)
            sender_subject = "Thank You for Your Testimonial"
            sender_template = 'emails/thank-you'
            sender_receiver = [testimonial.sender_email]  
            sender_merge_data = {
                'space_name': self.object.spaces_name,
                'testimonial_text': testimonial.testimonial_text,
                'user_name': testimonial.sender_name,
            }

            # Send the email to the space owner
            send_email.delay(subject=space_owner_subject, template_path=space_owner_template, 
                             receiver=space_owner_receiver, merge_data=space_owner_merge_data)

            # Send the email to the sender (thanking them)
            send_email.delay(subject=sender_subject, template_path=sender_template, 
                             receiver=sender_receiver, merge_data=sender_merge_data)

            url = self.request.build_absolute_uri(reverse('spaces_testimonials_detail', args=[self.object.slug]))

            messages.success(self.request, 'Testimonial Provided Successfully')
            return render(request, 'app/thankyou.html', {'url':url})
        
        return self.render_to_response(self.get_context_data(form=form))

class SpacesUpdateView(LoginRequiredMixin, UpdateView):
    model = Spaces
    form_class = SpacesForm
    template_name = "app/spaces_update.html"
    success_url = reverse_lazy('create_spaces') 

    def form_valid(self, form):
        messages.success(self.request, 'Space updated successfully!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.warning(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.user != self.request.user:
            messages.warning(self.request,'You do not have permission for this')
            return None
        return obj
    
    def dispatch(self, request, *args, **kwargs):
        spaces = self.get_object() 
        if spaces is None:
            return redirect('create_spaces') 
        return super().dispatch(request, *args, **kwargs)



class SpacesDetailView(LoginRequiredMixin, DetailView):
    model = Spaces
    template_name = 'app/spaces_details.html'   
    context_object_name = 'space'
    slug_url_kwarg = 'slug'   
    paginate_by = 6

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        space = self.object
        user = self.request.user

        wall_of_love_ids = WallofLove.objects.filter(user=user).values_list('testimonial_id', flat=True)

        testimonials_list = space.testimonials.all().order_by('-star_rating')
        paginator = Paginator(testimonials_list, self.paginate_by)  
        page_number = self.request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        context['page_obj'] = page_obj   
        context['testimonials'] = page_obj.object_list  

        wall_of_love = WallofLove.objects.filter(testimonial__spaces=space)
        context['wall_of_love_count'] = wall_of_love.count()
        context['wall_of_love_testimonials'] = [entry.testimonial for entry in wall_of_love]

        
        if testimonials_list.exists():
            total = testimonials_list.count()
            avg_rating = testimonials_list.filter(star_rating__isnull=False).aggregate(Avg('star_rating'))['star_rating__avg']
            context['average_rating'] = round(avg_rating, 1) if avg_rating else None
            context['total_testimonials'] = total
        
        context['wall_of_love_ids'] = set(wall_of_love_ids)  
        # Generate the embed URL
        embed_url = self.request.build_absolute_uri(reverse('embed_wall_of_love', args=[space.slug]))
        context['url'] = embed_url
        
        return context
    
    def dispatch(self, request, *args, **kwargs):
        space = self.get_object()
        # Check if the logged-in user is the space owner
        if space.user != request.user:
            messages.warning(request, 'You are not allowed to access this')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    

class SpacesDeleteView(LoginRequiredMixin, DeleteView):
    model = Spaces


    def post(self, request, *args, **kwargs):
        self.get_object().delete()
        redirect_url = request.POST.get('next', 'dashboard') 
        messages.success(request, 'Spaces successfully deleted')
        return redirect(redirect_url)
    
    def dispatch(self, request, *args, **kwargs):
        space = self.get_object()
        # Check if the logged-in user is the space owner
        if space.user != request.user:
            return HttpResponseForbidden("You are not allowed to delete this space.")
        return super().dispatch(request, *args, **kwargs)
    
def wall_of_love_json(request, slug):
    """
    View to display the embedding content from wall of love.  
    """
    space = get_object_or_404(Spaces, slug=slug)
    
    # Get all testimonials in WallOfLove for this space
    wall_of_love_testimonials = WallofLove.objects.filter(testimonial__spaces=space).values(
        'testimonial__testimonial_text',
        'testimonial__created_at',
        'testimonial__sender_name',
        'testimonial__star_rating',
        'testimonial__id'
    ).order_by('-testimonial__created_at')
    testimonials_json = json.dumps(list(wall_of_love_testimonials), default=str)
    # Prepare the data for JSON response
    response = render(request, 'app/embed_wall_of_love.html', {'testimonials_json': testimonials_json})
    response['X-Frame-Options'] = 'ALLOWALL'  
    return response


class TestimonialDeleteView(LoginRequiredMixin, DeleteView):
    model = Testimonials


    def post(self, request, *args, **kwargs):
        self.get_object().delete()
        redirect_url = request.POST.get('next', 'dashboard') 
        messages.success(request, 'Testimonial successfully deleted')
        return redirect(redirect_url)
    
    def dispatch(self, request, *args, **kwargs):
        testimonial = self.get_object()
        # Check if the logged-in user is the space owner
        if testimonial.spaces.user != request.user:
            return HttpResponseForbidden("You are not allowed to delete this testimonial.")
        return super().dispatch(request, *args, **kwargs)
    

class WallofLoveCreateView(LoginRequiredMixin, View):
    """
    View to create and remove the testimonial from wall of love.   
    """
    def post(self, request, testimonial_id):
        testimonial = get_object_or_404(Testimonials, id=testimonial_id)

         # Check if the testimonial is on the user's Wall of Love
        if wall_of_love_instance := WallofLove.objects.filter(
            user=request.user, testimonial=testimonial
        ):
            wall_of_love_instance.delete()
            messages.success(request, "Testimonial successfully removed from your Wall of Love!")
        else:
            WallofLove.objects.create(user=request.user, testimonial=testimonial)
            messages.success(request, "Testimonial successfully added to your Wall of Love!")

        redirect_url = request.POST.get('next', 'dashboard') 
        return redirect(redirect_url) 
    

class SpacesListView(LoginRequiredMixin, FilterView):
    """ View to list the spaces of the user with filtering capabilities"""
    model = Spaces
    template_name = 'app/spaces_list.html'
    context_object_name = 'spaces'
    filterset_class = SpacesFilter
    paginate_by = 5

    def get_queryset(self):
        user = self.request.user
        return (Spaces.objects
            .filter(user=user)
            .annotate(testimonial_count=Count('testimonials'))
            .distinct()
            ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['request'] = self.request  
        spaces = context['spaces']
        for space in spaces:
            space.generated_link = space.generate_space_details_link(self.request)
        return context
    
