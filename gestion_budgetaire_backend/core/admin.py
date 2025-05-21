from django.contrib import admin
from .models import (
    Utilisateur, Budget, Recette, Depense, DemandeDepense,
    Fournisseur, Commande, LigneBudgetaire, RapportFinancier,JournalAudit
)

# Admin personnalisé pour l'utilisateur
@admin.register(Utilisateur)
class UtilisateurAdmin(admin.ModelAdmin):
    list_display = ('email', 'nom', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('email', 'nom')
    ordering = ('-date_creation',)

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('exercice', 'montant_total', 'montant_disponible', 'statut', 'comptable')
    list_filter = ('statut',)
    search_fields = ('exercice',)

@admin.register(Recette)
class RecetteAdmin(admin.ModelAdmin):
    list_display = ('source', 'type', 'montant', 'date', 'budget')
    list_filter = ('type', 'date')

@admin.register(DemandeDepense)
class DemandeDepenseAdmin(admin.ModelAdmin):
    list_display = ('motif', 'montant_estime', 'statut', 'utilisateur', 'date_demande')
    list_filter = ('statut',)
    search_fields = ('motif',)

@admin.register(Depense)
class DepenseAdmin(admin.ModelAdmin):
    list_display = (
        'description', 'montant', 'type_depense', 'categorie', 'date',
        'est_planifiee', 'supervise_par', 'valide_par', 'statut_validation'
    )
    list_filter = ('type_depense', 'statut_validation', 'est_planifiee')
    search_fields = ('description',)

@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ('nom', 'type', 'email', 'telephone')
    search_fields = ('nom',)

@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ('reference', 'date', 'fournisseur', 'total', 'statut')
    list_filter = ('statut',)
    search_fields = ('reference',)

@admin.register(LigneBudgetaire)
class LigneBudgetaireAdmin(admin.ModelAdmin):
    list_display = ('id', 'article', 'montant_alloue', 'budget')


@admin.register(RapportFinancier)
class RapportFinancierAdmin(admin.ModelAdmin):
    list_display = ('periode', 'type', 'budget', 'date_generation', 'genere_par')
    list_filter = ('type', 'periode')




@admin.register(JournalAudit)
class JournalAuditAdmin(admin.ModelAdmin):
    list_display = ('utilisateur', 'action', 'date_heure')
    list_filter = ('utilisateur', 'date_heure')
    search_fields = ('action',)
