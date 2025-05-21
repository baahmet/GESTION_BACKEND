from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.timezone import now
from .models import (
    Utilisateur, Budget, Recette, Depense, DemandeDepense,
    Fournisseur, Commande, LigneBudgetaire, RapportFinancier,
    JournalAudit
)

# Audit création de budget
@receiver(post_save, sender=Budget)
def audit_budget(sender, instance, created, **kwargs):
    if created:
        JournalAudit.objects.create(
            utilisateur=instance.comptable,
            action=f"Création du budget {instance.exercice} - {instance.montant_total} F",
            date_heure=now()
        )

# Audit enregistrement de recette
@receiver(post_save, sender=Recette)
def audit_recette(sender, instance, created, **kwargs):
    if created:
        JournalAudit.objects.create(
            utilisateur=instance.budget.comptable,
            action=f"Recette ajoutée : {instance.source} - {instance.montant} F",
            date_heure=now()
        )

# Audit soumission de demande de dépense
@receiver(post_save, sender=DemandeDepense)
def audit_demande_depense(sender, instance, created, **kwargs):
    if created:
        JournalAudit.objects.create(
            utilisateur=instance.utilisateur,
            action=f"Demande de dépense soumise : {instance.motif} - {instance.montant_estime} F",
            date_heure=now()
        )

# Audit enregistrement de dépense
@receiver(post_save, sender=Depense)
def audit_depense(sender, instance, created, **kwargs):
    if created:
        JournalAudit.objects.create(
            utilisateur=instance.demande.utilisateur if instance.demande else None,
            action=f"Dépense enregistrée : {instance.description} - {instance.montant} F",
            date_heure=now()
        )

# Audit création de fournisseur
@receiver(post_save, sender=Fournisseur)
def audit_fournisseur(sender, instance, created, **kwargs):
    if created:
        JournalAudit.objects.create(
            utilisateur=None,
            action=f"Nouveau fournisseur ajouté : {instance.nom}",
            date_heure=now()
        )

# Audit création de commande
@receiver(post_save, sender=Commande)
def audit_commande(sender, instance, created, **kwargs):
    if created and instance.ligne_budgetaire.budget.comptable:
        JournalAudit.objects.create(
            utilisateur=instance.ligne_budgetaire.budget.comptable,
            action=f"Commande créée : {instance.reference} - {instance.quantite} × {instance.prix_unitaire} F",
            date_heure=now()
        )


# Audit ajout de ligne budgétaire
@receiver(post_save, sender=LigneBudgetaire)
def audit_ligne_budgetaire(sender, instance, created, **kwargs):
    if created:
        JournalAudit.objects.create(
            utilisateur=instance.budget.comptable,
            action=f"Ligne budgétaire ajoutée : {instance.article} - {instance.montant_alloue} F",
            date_heure=now()
        )


# Audit génération rapport financier
@receiver(post_save, sender=RapportFinancier)
def audit_rapport(sender, instance, created, **kwargs):
    if created:
        JournalAudit.objects.create(
            utilisateur=instance.genere_par,
            action=f"Rapport généré pour {instance.periode} ({instance.type.upper()})",
            date_heure=now()
        )

# Audit suppression de budget (exemple delete)
@receiver(post_delete, sender=Budget)
def audit_budget_suppression(sender, instance, **kwargs):
    JournalAudit.objects.create(
        utilisateur=instance.comptable,
        action=f"Budget supprimé : {instance.exercice}",
        date_heure=now()
    )
   #validation depense
@receiver(post_save, sender=Depense)
def audit_validation_depense(sender, instance, created, **kwargs):
    if not created and instance.statut_validation in ['validee', 'rejettee']:
        JournalAudit.objects.create(
            utilisateur=instance.valide_par,
            action=f"Dépense {instance.description} {instance.statut_validation.upper()} par le Directeur - {instance.montant} F",
            date_heure=now()
        )

#audit depense supervisé
@receiver(post_save, sender=Depense)
def audit_supervision_depense(sender, instance, created, **kwargs):
    if not created and instance.supervise_par:
        JournalAudit.objects.get_or_create(  # Évite doublons
            utilisateur=instance.supervise_par,
            action=f"Dépense {instance.description} supervisée par le CSA",
            date_heure=now()
        )

#audit validation commande



