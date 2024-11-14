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
from .forms import SpacesForm, QuestionFormSet, TestimonialForm, QuestionForm
from django_filters.views import FilterView
from .filters import SpacesFilter
from .tasks import send_email
import json
import logging
from subscriptions.decorators import subscription_required
from django.utils.decorators import method_decorator
from django.db import transaction
from django.contrib.auth.decorators import login_required


logger = logging.getLogger(__name__)
@subscription_required(min_access_level=1)
def test_view(request):
    testimonials_count = Testimonials.objects.filter(spaces__user=request.user).count()
    testimonials_count_limit = request.subscription.plan.get_limit('testimonials_count')
    if testimonials_count > testimonials_count_limit:
        return HttpResponse('Limit exceeded')
    return HttpResponse("On limit")


@method_decorator(subscription_required(min_access_level=1), name='dispatch')
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'app/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        try:
            # Retrieve user's spaces with testimonials prefetch
            spaces = Spaces.objects.filter(user=user).prefetch_related('testimonials')
            context['spaces'] = spaces
            context['spaces_count'] = spaces.count()

            # Retrieve recent testimonials, limited to 5 most recent
            context['recent_testimonials'] = Testimonials.objects.filter(spaces__user=user).order_by('-created_at')[:5]
            context['testimonial_count'] = Testimonials.objects.filter(spaces__user=user).count()

            # Generate links for each space
            for space in spaces:
                try:
                    space.generated_link = space.generate_space_details_link(self.request)
                    logger.debug(f"Generated link for space ID {space.id}")
                except Exception as e:
                    logger.error(f"Error generating link for space ID {space.id}: {e}")
            
            logger.info(f"Dashboard loaded for user {user} with {context['spaces_count']} spaces and {context['testimonial_count']} testimonials.")

        except Exception as e:
            logger.error(f"Error loading dashboard for user {user}: {e}")
            context['spaces'] = []
            context['spaces_count'] = 0
            context['recent_testimonials'] = []
            context['testimonial_count'] = 0

        return context

class SpacesCreateView(LoginRequiredMixin, CreateView):
    """
    View to create a Space with questions.
    """
    model = Spaces
    form_class = SpacesForm
    template_name = 'app/create_space.html'
    success_url = reverse_lazy('spaces_list')

    def dispatch(self, request, *args, **kwargs):
        # Apply subscription check on POST requests
        if request.method == 'POST':
            decorated_view = subscription_required(min_access_level=1, redirect_url=request.path)(super().dispatch)
            return decorated_view(request, *args, **kwargs)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['formset'] = QuestionFormSet(self.request.POST or None, self.request.FILES or None)
        # Retrieve subscription limits from the plan
        context['max_questions'] = self.request.subscription.plan.get_limit('max_questions')
        context['max_spaces'] = self.request.subscription.plan.get_limit('max_spaces')
        context['user_spaces_count'] = Spaces.objects.filter(user=self.request.user).count()

        return context

    def validate_formset(self, formset, max_questions):
        """
        Helper method to validate the formset and ensure no exceeding of question limits.
        """
        if len(formset) > max_questions:
            
            return False, f"You can only add up to {max_questions} questions."
        
        if not any(
            question_form.cleaned_data and not question_form.cleaned_data.get('DELETE', False)
            for question_form in formset
        ):
            return False, "Please add at least one question."
        
        return True, ""

    def form_valid(self, form):
        """
        Handles form validation and saving of space and questions.
        """
        max_spaces = self.request.subscription.plan.get_limit('max_spaces')
        max_questions = self.request.subscription.plan.get_limit('max_questions')

        # Check if the user has exceeded the space limit
        current_space_count = Spaces.objects.filter(user=self.request.user).count()
        if max_spaces is not None and current_space_count >= max_spaces:
            messages.warning(self.request, "You have reached the maximum number of spaces allowed for your subscription plan.")
            form.add_error(None, "You have reached the maximum number of spaces allowed for your subscription plan. Please Upgrade.")
            return self.form_invalid(form)

        context = self.get_context_data()
        formset = context['formset']
         # Validate the formset
        if not formset.is_valid():
            messages.warning(self.request, "Please correct the errors in the questions.")
            return self.form_invalid(form)

        # Validate the formset for question limit and empty questions
        is_valid, error_message = self.validate_formset(formset, max_questions)
        if not is_valid:
            messages.warning(self.request, error_message)
            form.add_error(None, error_message)
            return self.form_invalid(form)

       
        try:
            # Start atomic transaction to ensure all or nothing saving
            with transaction.atomic():
                # Save the space instance
                space = form.save(commit=False)
                space.user = self.request.user
                space.save()

                # Save associated formset (questions)
                formset.instance = space
                formset.save()

                logger.info(f"Space created successfully by {self.request.user} with {len(formset)} questions.")
                messages.success(self.request, "Space with questions created successfully")
                return redirect(self.success_url)

        except ValidationError as e:
            # Log validation errors
            logger.error(f"ValidationError during space creation: {e}")
            for field, errors in e.message_dict.items():
                for error in errors:
                    form.add_error(field, error)
            return self.form_invalid(form)

        except Exception as e:
            # Log unexpected errors
            logger.error(f"Unexpected error during space creation: {e}")
            messages.error(self.request, "An error occurred while creating the space. Please try again.")
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




@method_decorator(subscription_required(min_access_level=1), name='dispatch')
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

        # Retrieve subscription limit with exception handling
        try:
            max_testimonials = self.request.subscription.plan.get_limit('testimonials_count')
        except AttributeError as e:
            max_testimonials = None
            logger.error(f"Failed to retrieve testimonial limit for user {user.id}: {e}")

        wall_of_love_ids = WallofLove.objects.filter(user=user).values_list('testimonial_id', flat=True)

        testimonials_list = space.testimonials.all().order_by('created_at')
       
        if max_testimonials:
            testimonials = testimonials_list[:max_testimonials]
            has_more_testimonials = max_testimonials and testimonials_list.count() > max_testimonials
        else:
            testimonials = testimonials_list
            has_more_testimonials = False

        paginator = Paginator(testimonials, self.paginate_by)
        page_number = self.request.GET.get('page', 1)
        
        # Paginate and log any potential issues
        try:
            page_obj = paginator.get_page(page_number)
        except Exception as e:
            logger.error(f"Pagination error on page {page_number} for space {space.id}: {e}")
            page_obj = paginator.get_page(1)  # Fallback to the first page

        context['page_obj'] = page_obj   
        context['testimonials'] = page_obj.object_list  
        context['max_testimonials'] = max_testimonials
        context['has_more_testimonials'] = has_more_testimonials 

        wall_of_love = WallofLove.objects.filter(testimonial__spaces=space)
        context['wall_of_love_count'] = wall_of_love.count()
        context['wall_of_love_testimonials'] = [entry.testimonial for entry in wall_of_love]

        if testimonials_list.exists():
            total = testimonials_list.count()
            avg_rating = testimonials_list.filter(star_rating__isnull=False).aggregate(Avg('star_rating'))['star_rating__avg']
            context['average_rating'] = round(avg_rating, 1) if avg_rating else None
            context['total_testimonials'] = total

        context['wall_of_love_ids'] = set(wall_of_love_ids)

        # Generate and log the embed URL
        try:
            embed_url = self.request.build_absolute_uri(reverse('embed_wall_of_love', args=[space.slug]))
            context['url'] = embed_url
        except Exception as e:
            logger.error(f"Failed to generate embed URL for space {space.id}: {e}")
            context['url'] = None

        return context

    def dispatch(self, request, *args, **kwargs):
        try:
            space = self.get_object()
            # Verify ownership
            if space.user != request.user:
                messages.warning(request, 'You are not allowed to access this')
                return redirect('dashboard')
            return super().dispatch(request, *args, **kwargs)
        except Spaces.DoesNotExist:
            logger.warning(f"Space with slug {kwargs.get('slug')} not found for user {request.user.id}")
            messages.error(request, 'Requested space does not exist')
            return redirect('dashboard')
        except Exception as e:
            logger.error(f"Unexpected error during dispatch for user {request.user.id}: {e}")
            messages.error(request, 'An error occurred. Please try again later.')
            return redirect('dashboard')

    
@method_decorator(subscription_required(min_access_level=1), name='dispatch')
class SpacesDeleteView(LoginRequiredMixin, DeleteView):
    model = Spaces

    def post(self, request, *args, **kwargs):
        space = self.get_object()
        try:
            space.delete()
            messages.success(request, 'Space successfully deleted')
            logger.info(f"User {request.user} deleted space ID {space.id}")
        except Exception as e:
            logger.error(f"Error deleting space ID {space.id} by user {request.user}: {e}")
            messages.error(request, "An error occurred while deleting the space. Please try again.")
        
        redirect_url = request.POST.get('next', 'dashboard') 
        return redirect(redirect_url)

    def dispatch(self, request, *args, **kwargs):
        space = self.get_object()
        
        # Check if the logged-in user is the space owner
        if space.user != request.user:
            logger.warning(f"Unauthorized delete attempt by user {request.user} for space ID {space.id}")
            return HttpResponseForbidden("You are not allowed to delete this space.")
        
        return super().dispatch(request, *args, **kwargs)
    

@subscription_required(min_access_level=1)
def wall_of_love_json(request, slug):
    """
    View to display the embedding content from wall of love.  
    """
    space = get_object_or_404(Spaces, slug=slug)
    subscription_plan_name =  request.subscription.plan.name

    
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
    response = render(request, 'app/embed_wall_of_love.html', {'testimonials_json': testimonials_json, 'subscription':subscription_plan_name})
    response['X-Frame-Options'] = 'ALLOWALL'  
    return response


@method_decorator(subscription_required(min_access_level=1), name='dispatch')
class TestimonialDeleteView(LoginRequiredMixin, DeleteView):
    model = Testimonials

    def post(self, request, *args, **kwargs):
        testimonial = self.get_object()
        try:
            testimonial.delete()
            messages.success(request, 'Testimonial successfully deleted')
            logger.info(f"User {request.user} deleted testimonial ID {testimonial.id}")
        except Exception as e:
            logger.error(f"Error deleting testimonial ID {testimonial.id} by user {request.user}: {e}")
            messages.error(request, "An error occurred while deleting the testimonial. Please try again.")
        
        redirect_url = request.POST.get('next', 'dashboard') 
        return redirect(redirect_url)

    def dispatch(self, request, *args, **kwargs):
        testimonial = self.get_object()
        
        # Check if the logged-in user is the space owner
        if testimonial.spaces.user != request.user:
            logger.warning(f"Unauthorized delete attempt by user {request.user} for testimonial ID {testimonial.id}")
            return HttpResponseForbidden("You are not allowed to delete this testimonial.")
        
        return super().dispatch(request, *args, **kwargs)
    

@method_decorator(subscription_required(min_access_level=1), name='dispatch')
class WallofLoveCreateView(LoginRequiredMixin, View):
    """
    View to create and remove a testimonial from the Wall of Love.
    """
    def post(self, request, testimonial_id):
        testimonial = get_object_or_404(Testimonials, id=testimonial_id)
        
        try:
            max_testimonials = request.subscription.plan.get_limit('testimonials_count')

            # Check if the testimonial is already on the user's Wall of Love
            wall_of_love_instance = WallofLove.objects.filter(user=request.user, testimonial=testimonial)

            wall_of_love_count =wall_of_love_instance.count()


            if wall_of_love_instance.exists():
                # Remove testimonial if it already exists
                wall_of_love_instance.delete()
                messages.success(request, "Testimonial successfully removed from your Wall of Love!")
                logger.info(f"User {request.user} removed a testimonial (ID: {testimonial_id}) from Wall of Love.")
            else:
                # Check if user has reached max testimonials limit
                if wall_of_love_count >= max_testimonials:
                    messages.warning(request, "You have reached the maximum number of testimonials allowed on wall of love. Please Upgrade to add more")
                    logger.warning(f"User {request.user} attempted to add testimonial (ID: {testimonial_id}) but exceeded limit.")
                else:
                    # Add testimonial if limit has not been reached
                    WallofLove.objects.create(user=request.user, testimonial=testimonial)
                    messages.success(request, "Testimonial successfully added to your Wall of Love!")
                    logger.info(f"User {request.user} added a testimonial (ID: {testimonial_id}) to Wall of Love.")

        except Exception as e:
            logger.error(f"An error occurred while processing the Wall of Love action for user {request.user} with testimonial ID {testimonial_id}: {e}")
            messages.error(request, "An error occurred while processing your request. Please try again later.")
        
        redirect_url = request.POST.get('next', 'dashboard') 
        return redirect(redirect_url)
    
@method_decorator(subscription_required(min_access_level=1), name='dispatch')
class SpacesListView(LoginRequiredMixin, FilterView):
    """
    View to list the spaces of the user with filtering capabilities.
    """
    model = Spaces
    template_name = 'app/spaces_list.html'
    context_object_name = 'spaces'
    filterset_class = SpacesFilter
    paginate_by = 5

    def get_queryset(self):
        user = self.request.user
        try:
            queryset = (
                Spaces.objects
                .filter(user=user)
                .annotate(testimonial_count=Count('testimonials'))
                .distinct()
                .order_by('-created_at')
            )
            return queryset
        except Exception as e:
            logger.error(f"Error retrieving spaces for user {user}: {e}")
            return Spaces.objects.none()  
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['request'] = self.request
        
        # Generate links for each space and add to context
        spaces = context.get('spaces', [])
        for space in spaces:
            try:
                space.generated_link = space.generate_space_details_link(self.request)
            except Exception as e:
                logger.error(f"Error generating link for space ID {space.id}: {e}")
        
        return context
    

@login_required
@subscription_required(min_access_level=1)
def update_space(request, slug):
    """ 
    View to update spaces and related questions.
    """
    try:
        # Retrieve the space object or raise a 404 error if not found
        space = get_object_or_404(Spaces, slug=slug)
        
        # Check if the current user is the owner of the space
        if space.user != request.user:
            logger.error(f"Unauthorized access attempt by user {request.user} on space {slug}.")
            messages.warning(request, "You are not authorized to perform this action.")
            return redirect('spaces_list')  # Redirect to a page showing the user's own spaces

        max_questions = request.subscription.plan.get_limit('max_questions')

        if request.method == 'POST':
            form = SpacesForm(request.POST, request.FILES, instance=space)
            formset = QuestionFormSet(request.POST, instance=space)

            if form.is_valid() and formset.is_valid():
                # Filter out empty forms (those with no cleaned data)
                non_empty_forms = [f for f in formset.forms if f.cleaned_data and any(f.cleaned_data.values())]
                if len(non_empty_forms) > max_questions:
                    messages.warning(request, f"You can only add up to {max_questions} questions.")
                    return redirect(request.path)
                else:
                    # Save the form and formset
                    form.save()
                    formset.save()
                    logger.info(f"Space {slug} updated successfully by user {request.user}.")
                    messages.success(request, 'Update Successful')
                    return redirect('spaces_detail', slug=space.slug)  # Redirect to the detail view
            else:
                # Log validation errors
                logger.error(f"Form validation failed for user {request.user} on space {slug}. Errors: {form.errors}, {formset.errors}")
        else:
            form = SpacesForm(instance=space)
            formset = QuestionFormSet(instance=space)

        return render(request, 'app/spaces_update.html', {
            'form': form,
            'formset': formset,
            'space': space,
            'max_questions': max_questions
        })

    except Exception as e:
        # Log unexpected errors
        logger.exception(f"Unexpected error occurred while updating space {slug} for user {request.user}. Error: {str(e)}")
        messages.error(request, "An unexpected error occurred. Please try again later.")
        return redirect('spaces_list')