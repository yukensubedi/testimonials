from django.urls import path
from .views import(
    test_view,
    SpacesCreateView,
    SpacesDetailView, 
    SpacesUpdateView,
    DashboardView,
    TestimonialCollectView, 
    WallofLoveView, 
    TestimonialDeleteView, 
    WallofLoveListView,
    SpacesListView, 
    EmbedWallOfLoveView

)

urlpatterns = [
    path('test/', test_view, name='test'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('spaces/', SpacesListView.as_view(), name='spaces_list'),

    path('spaces/create/', SpacesCreateView.as_view(), name='create_spaces'),
    path('spaces/<int:pk>/edit/', SpacesUpdateView.as_view(), name='spaces_update'),
    path('spaces/<slug:slug>/', SpacesDetailView.as_view(), name='spaces_detail'),
    path('wall-of-love/<int:testimonial_id>/', WallofLoveView.as_view(), name='wall_of_love'),
    path('spaces/testimonial/delete/<int:pk>/', TestimonialDeleteView.as_view(), name='testimonial_delete'),
    path('wall-of-love/', WallofLoveListView.as_view(), name='wall_of_love_list'),
    path('<slug>/', TestimonialCollectView.as_view(), name='spaces_testimonials_detail'),

     path('embed/wall-of-love/<slug:slug>/', EmbedWallOfLoveView.as_view(), name='embed_wall_of_love'),


]
