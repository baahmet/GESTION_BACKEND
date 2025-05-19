from .models import JournalAudit, Notification
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
    montant_total_depenses_validees = serializers.SerializerMethodField()
    montant_total_recettes = serializers.SerializerMethodField()
    montant_disponible = serializers.SerializerMethodField()

    class Meta:
        model = Budget
        fields = '__all__'
        read_only_fields = (
            'montant_total_depenses_validees',
            'montant_total_recettes',
            'montant_disponible',
        )

    def get_montant_total_depenses_validees(self, obj):
        return obj.montant_total_depenses_validees

    def get_montant_total_recettes(self, obj):
        return obj.montant_total_recettes

    def get_montant_disponible(self, obj):
        return obj.montant_disponible


class RapportFinancierSerializer(serializers.ModelSerializer):
    genere_par_nom = serializers.SerializerMethodField()

    class Meta:
        model = RapportFinancier
        fields = '__all__'
        read_only_fields = ['nom_fichier', 'fichier', 'date_generation', 'genere_par']

    def get_genere_par_nom(self, obj):
        if obj.genere_par:
            return obj.genere_par.nom  # Accès au champ 'nom' de Utilisateur
        return "Inconnu"

    def create(self, validated_data):
        budget = validated_data['budget']
        periode = validated_data['periode']
        type_rapport = validated_data['type']

        # Générer automatiquement le nom du fichier
        validated_data['nom_fichier'] = f"rapport_{budget.exercice}_{periode}.{type_rapport}"

        # L'utilisateur connecté est le générateur (on va le fixer ici)
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['genere_par'] = request.user

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



class UpdateMyAccountSerializer(serializers.ModelSerializer):
    mot_de_passe = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Utilisateur
        fields = ['nom', 'email', 'mot_de_passe']

    def update(self, instance, validated_data):
        if 'mot_de_passe' in validated_data:
            instance.set_password(validated_data.pop('mot_de_passe'))
        return super().update(instance, validated_data)






class NotificationSerializer(serializers.ModelSerializer):
    utilisateur_nom = serializers.CharField(source='utilisateur.nom', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'message', 'date_creation', 'niveau', 'lu', 'utilisateur_nom']

