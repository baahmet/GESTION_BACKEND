from .models import JournalAudit
from rest_framework import serializers
from .models import (
    Utilisateur, Budget, Recette, Depense,
    DemandeDepense, Fournisseur, Commande,
    LigneBudgetaire, RapportFinancier
)



# serialiseur qui permet de transformer les objet view en api
class UtilisateurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Utilisateur
        fields = ['id', 'email', 'nom', 'role', 'date_creation']




class RecetteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recette
        fields = '__all__'

class DemandeDepenseSerializer(serializers.ModelSerializer):
    utilisateur_nom = serializers.CharField(source='utilisateur.nom', read_only=True)
    class Meta:
        model = DemandeDepense
        fields = '__all__'
        read_only_fields = ['utilisateur']

class DepenseSerializer(serializers.ModelSerializer):
    ligne_budgetaire_nom = serializers.CharField(source="ligne_budgetaire.article", read_only=True)

    class Meta:
        model = Depense
        fields = '__all__'

class FournisseurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fournisseur
        fields = '__all__'


class CommandeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commande
        fields = '__all__'
        read_only_fields = ['total']

class LigneBudgetaireSerializer(serializers.ModelSerializer):

    class Meta:
        model = LigneBudgetaire
        fields = '__all__'



class BudgetSerializer(serializers.ModelSerializer):
    recettes = RecetteSerializer(many=True, read_only=True)
    depenses = DepenseSerializer(many=True, read_only=True)
    lignes = LigneBudgetaireSerializer(many=True, read_only=True)
    class Meta:
        model = Budget
        fields = '__all__'

class RapportFinancierSerializer(serializers.ModelSerializer):
    class Meta:
        model = RapportFinancier
        fields = '__all__'
        read_only_fields = ['nom_fichier', 'fichier', 'date_generation', 'genere_par']

    def create(self, validated_data):
        budget = validated_data['budget']
        periode = validated_data['periode']
        type_rapport = validated_data['type']

        # Générer nom_fichier auto
        validated_data['nom_fichier'] = f"rapport_{budget.exercice}_{periode}.{type_rapport}"

        # On crée l'objet sans fichier (sera ajouté après génération réelle)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data["budget"] = validated_data.get("budget", instance.budget)
        return super().update(instance, validated_data)




class JournalAuditSerializer(serializers.ModelSerializer):
    utilisateur_nom = serializers.SerializerMethodField()
    utilisateur_email = serializers.SerializerMethodField()

    class Meta:
        model = JournalAudit
        fields = ['id', 'utilisateur_nom', 'utilisateur_email', 'action', 'date_heure']

    def get_utilisateur_nom(self, obj):
        return obj.utilisateur.nom if obj.utilisateur else "Inconnu"

    def get_utilisateur_email(self, obj):
        return obj.utilisateur.email if obj.utilisateur else "Inconnu"



class RegisterSerializer(serializers.ModelSerializer):
    mot_de_passe = serializers.CharField(write_only=True)

    class Meta:
        model = Utilisateur
        fields = ['id', 'email', 'nom', 'role', 'mot_de_passe']

    def create(self, validated_data):
        mot_de_passe = validated_data.pop('mot_de_passe')
        utilisateur = Utilisateur(**validated_data)
        utilisateur.set_password(mot_de_passe)

