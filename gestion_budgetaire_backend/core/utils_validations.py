from rest_framework import serializers
from django.db.models import Sum

def verifier_ligne_budgetaire_autorisee(budget, montant_ligne):
    if montant_ligne > budget.montant_disponible:
        raise serializers.ValidationError(
            f"La ligne dépasse le montant disponible du budget ({budget.montant_disponible} F)."
        )

def verifier_commande_autorisee(ligne, total_commande):
    if total_commande > ligne.montant_alloue:
        raise serializers.ValidationError(
            f"La commande dépasse la ligne budgétaire ({ligne.montant_alloue} F)."
        )

def verifier_depense_autorisee(budget, montant_depense):
    if montant_depense > budget.montant_disponible:
        raise serializers.ValidationError(
            f"La dépense dépasse le budget disponible ({budget.montant_disponible} F)."
        )
