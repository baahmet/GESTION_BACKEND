# core/filters.py

import django_filters
from .models import JournalAudit

class JournalAuditFilter(django_filters.FilterSet):
    date_debut = django_filters.DateFilter(field_name="date_heure", lookup_expr='gte')
    date_fin = django_filters.DateFilter(field_name="date_heure", lookup_expr='lte')
    utilisateur = django_filters.CharFilter(field_name="utilisateur__email", lookup_expr='icontains')

    class Meta:
        model = JournalAudit
        fields = ['utilisateur', 'date_debut', 'date_fin']
