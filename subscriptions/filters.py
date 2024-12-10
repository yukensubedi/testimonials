from django_filters import FilterSet, CharFilter, ChoiceFilter, DateFilter
from .models import Payment

class PaymentFilter(FilterSet):
    """
    Define filters for the Payment model with user-friendly date fields.
    """
    status = ChoiceFilter(choices=Payment.PAYMENT_STATUS, label="Status")
    transaction_id = CharFilter(field_name="transaction_id", lookup_expr="icontains", label="Transaction ID")
    created_at_from = DateFilter(
        field_name="created_at",
        lookup_expr="gte",
        label="From Date",
    )
    created_at_to = DateFilter(
        field_name="created_at",
        lookup_expr="lte",
        label="To Date",
    )

    class Meta:
        model = Payment
        fields = ['status', 'transaction_id', 'created_at_from', 'created_at_to']
