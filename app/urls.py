from django.urls import path
from .views import(
    test_view,
    SpacesCreateView,
    SpacesDetailView, 
    SpacesUpdateView,
    DashboardView,
    TestimonialCollectView, 
    WallofLoveCreateView, 
    TestimonialDeleteView, 
    SpacesListView, 
    wall_of_love_json,
    SpacesDeleteView

)

urlpatterns = [
    path('test/', test_view, name='test'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('spaces/', SpacesListView.as_view(), name='spaces_list'),
    path('spaces/delete/<int:pk>/', SpacesDeleteView.as_view(), name='spaces_delete'),

    path('spaces/create/', SpacesCreateView.as_view(), name='create_spaces'),
    path('spaces/<int:pk>/edit/', SpacesUpdateView.as_view(), name='spaces_update'),
    path('spaces/<slug:slug>/', SpacesDetailView.as_view(), name='spaces_detail'),
    path('wall-of-love/<int:testimonial_id>/', WallofLoveCreateView.as_view(), name='wall_of_love'),
    path('spaces/testimonial/delete/<int:pk>/', TestimonialDeleteView.as_view(), name='testimonial_delete'),
    path('<slug>/', TestimonialCollectView.as_view(), name='spaces_testimonials_detail'),

    path('embed/<slug:slug>/', wall_of_love_json, name='embed_wall_of_love'),



]
