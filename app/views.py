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
from django.http import HttpResponseForbidden, HttpResponse

from .models import Spaces, Question, Testimonials, WallofLove
from .forms import SpacesForm, QuestionFormSet, TestimonialForm
from django_filters.views import FilterView
from .filters import SpacesFilter


def test_view(request):
    messages.warning(request, 'Test Complete')
    return render(request, 'app/test.html')

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
    model = Spaces
    form_class = SpacesForm
    template_name = 'app/create_space.html'
    success_url = reverse_lazy('create_spaces')   
    max_questions = 2

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = QuestionFormSet(self.request.POST)
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
        
        if not formset:
            messages.warning(self.request, "No questions added")
            return self.form_invalid(form)

        if form.is_valid() and formset.is_valid():
            space = form.save(commit=False)
            space.user = self.request.user
            space.save()  
            
            formset.instance = space  
            formset.save()   
            messages.success(self.request, "Spaces with questions created successfully")
            return redirect(self.success_url)
        else:
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
        print(self.object.id)
        
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
            messages.success(self.request, 'Testimonial Provided Successfully')
            # todo: Redirect to dynamic thankyou page
            return redirect(reverse('spaces_detail', args=[self.object.slug]))  
        
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
    template_name = 'app/test.html'   
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
        
        return context
    
  
        
class EmbedWallOfLoveView(ListView):
    model = WallofLove
    template_name = "app/embed_wall_of_love.html"
    context_object_name = 'wall_of_love_testimonials'

    def get_queryset(self):
        slug = self.kwargs.get("slug")
        space = get_object_or_404(Spaces, slug=slug)

        return WallofLove.objects.filter(testimonial__spaces= space).order_by('-created_at')
    
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        response["X-Frame-Options"] = "ALLOWALL"  # Allow embedding in iframes
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['space'] = get_object_or_404(Spaces, slug=self.kwargs['slug'])
        return context


           
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
    

class WallofLoveView(LoginRequiredMixin, View):
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
    

class WallofLoveListView(LoginRequiredMixin, ListView):
    model = Spaces
    template_name = 'app/walloflovelist.html'  # Update with your actual template name
    context_object_name = 'spaces'

    def get_queryset(self):
        # Get the logged-in user's Wall of Love testimonials
        user_wall_of_love = WallofLove.objects.filter(user=self.request.user)
        # Annotate spaces with the count of testimonials in the Wall of Love
        return (Spaces.objects
                .filter(testimonials__in=user_wall_of_love.values('testimonial'))
                .annotate(testimonial_count=Count('testimonials'))
                .distinct())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['wall_of_love'] = WallofLove.objects.filter(user=self.request.user)
        
        return context
    
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
    
  