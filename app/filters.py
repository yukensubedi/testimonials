from django_filters import rest_framework as filters
from django_filters import FilterSet, CharFilter, ChoiceFilter
from .models import Spaces

class SpacesFilter(FilterSet):
    spaces_name = filters.CharFilter(lookup_expr='icontains')
    header_title = filters.CharFilter(lookup_expr='icontains')
    star_rating = filters.BooleanFilter()
    created_at = filters.DateFromToRangeFilter()
    
    class Meta:
        model = Spaces
        fields = ['spaces_name', 'header_title', 'star_rating', 'created_at']