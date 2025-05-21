# core/views.py
from django.http import FileResponse
from rest_framework.decorators import action

from .utils.rapport_generator import generate_rapport_file
from .utils_validations import verifier_ligne_budgetaire_autorisee
from .utils_validations import verifier_depense_autorisee
from django.db import models
from rest_framework import serializers
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from .models import (
    Budget, Recette, Depense, DemandeDepense,
    Fournisseur, Commande, LigneBudgetaire, RapportFinancier,Utilisateur
)
from .serializers import (
    BudgetSerializer, RecetteSerializer, DepenseSerializer,
    DemandeDepenseSerializer, FournisseurSerializer,
    CommandeSerializer, LigneBudgetaireSerializer,
    RapportFinancierSerializer, UtilisateurSerializer
)
from .permissions import IsComptable, IsDirecteur, IsCSA
from rest_framework.views import APIView
from django.utils import timezone
from rest_framework.response import Response

from rest_framework.viewsets import ReadOnlyModelViewSet
from .serializers import JournalAuditSerializer
from rest_framework import status
from .serializers import RegisterSerializer
from django_filters.rest_framework import DjangoFilterBackend
from .filters import JournalAuditFilter


class UtilisateurViewSet(ReadOnlyModelViewSet):
    """
    Vue REST lecture seule des utilisateurs.
    (Réservée au Comptable, ou adaptatif selon besoins)
    """
    queryset = Utilisateur.objects.all()
    serializer_class = UtilisateurSerializer
    permission_classes = [IsAuthenticated, IsComptable]

class BudgetViewSet(ModelViewSet):
    """
    Vue REST pour gérer les budgets (réservé au Comptable)
    """
    queryset = Budget.objects.all()
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated, IsComptable]


class RecetteViewSet(ModelViewSet):
    """
    Vue REST pour gérer les recettes budgétaires
    """
    queryset = Recette.objects.all()
    serializer_class = RecetteSerializer
    permission_classes = [IsAuthenticated, IsComptable]

    def perform_create(self, serializer):
        recette = serializer.save()

        # Mise à jour du montant_disponible du budget concerné
        budget = recette.budget
        budget.montant_disponible += recette.montant
        budget.save()



class DemandeDepenseViewSet(ModelViewSet):
    """
    Vue REST pour soumettre ou consulter des demandes de dépense
    """
    queryset = DemandeDepense.objects.all()
    serializer_class = DemandeDepenseSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # Associer automatiquement l'utilisateur connecté
        serializer.save(utilisateur=self.request.user)



class SupervisionDepenseView(APIView):
    permission_classes = [IsAuthenticated, IsCSA]

    @swagger_auto_schema(
        operation_description="Supervision d’une dépense par le CSA",
        responses={200: openapi.Response('Dépense supervisée')}
    )

    def post(self, request, pk):
        depense = Depense.objects.get(pk=pk)

        if depense.supervise_par:
            return Response({"error": "Cette dépense a déjà été supervisée."}, status=400)

        depense.supervise_par = request.user
        depense.save()
        return Response({"message": "Supervision effectuée avec succès."})



class ValidationDepenseView(APIView):
    permission_classes = [IsAuthenticated, IsDirecteur]

    @swagger_auto_schema(
        operation_description="Validation ou rejet d’une dépense par le Directeur",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'statut_validation': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['validee', 'rejettee'],
                    description="Statut final de la dépense"
                )
            },
            required=['statut_validation']
        ),
        responses={200: openapi.Response('Dépense validée ou rejetée')}
    )
    def post(self, request, pk):
        depense = Depense.objects.get(pk=pk)

        if not depense.supervise_par:
            return Response({"error": "La dépense doit d'abord être supervisée."}, status=403)

        if depense.statut_validation != 'en_attente':
            return Response({"error": "Cette dépense a déjà été traitée."}, status=400)

        action = request.data.get("statut_validation")
        if action not in ['validee', 'rejettee']:
            return Response({"error": "Statut non valide"}, status=400)

        depense.statut_validation = action
        depense.valide_par = request.user
        depense.date_validation = timezone.now()
        depense.save()

        # 🔁 Si validée → diminuer le budget
        if action == 'validee':
            verifier_depense_autorisee(depense.budget, depense.montant)
            budget = depense.budget
            if depense.montant > budget.montant_disponible:
                return Response({"error": "Le budget disponible est insuffisant."}, status=400)
            budget.montant_disponible -= depense.montant
            budget.save()

        return Response({"message": f"Dépense {action}."})


from .utils_validations import verifier_commande_autorisee
from .models import JournalAudit
from django.utils.timezone import now

class ValidationCommandeView(APIView):
    permission_classes = [IsAuthenticated, IsComptable]

    @swagger_auto_schema(
        operation_description="Valider ou rejeter une commande",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'statut': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['validee', 'rejettee'],
                    description="Statut final de la commande"
                )
            },
            required=['statut']
        ),
        responses={200: openapi.Response('Commande traitée')}
    )
    def post(self, request, pk):
        commande = Commande.objects.get(pk=pk)
        ligne = commande.ligne_budgetaire
        montant = commande.quantite * commande.prix_unitaire

        if commande.statut != 'en_attente':
            return Response({"error": "Commande déjà traitée."}, status=400)

        action = request.data.get('statut')
        if action == 'validee':
            verifier_commande_autorisee(ligne, montant)
            if montant > ligne.montant_alloue:
                return Response({"error": "Montant de la commande dépasse la ligne budgétaire."}, status=400)

            ligne.montant_alloue -= montant
            ligne.save()

        commande.statut = action
        commande.save()

        # ✅ Enregistrement de l'audit ici
        JournalAudit.objects.create(
            utilisateur=request.user,
            action=f"Commande {commande.reference} {action.upper()} - {montant} F",
            date_heure=now()
        )

        return Response({"message": f"Commande {action}."})


class DepenseViewSet(ModelViewSet):
    """
    Vue REST pour enregistrer ou consulter les dépenses
    """
    queryset = Depense.objects.all()
    serializer_class = DepenseSerializer
    permission_classes = [IsAuthenticated, IsComptable]

    def perform_create(self, serializer):
        budget = serializer.validated_data['budget']
        if budget.statut == 'cloture':
            raise serializers.ValidationError("Ce budget est clôturé. Vous ne pouvez plus y ajouter de dépense.")
        serializer.save()



class FournisseurViewSet(ModelViewSet):
    """
    Vue REST pour gérer les fournisseurs
    """
    queryset = Fournisseur.objects.all()
    serializer_class = FournisseurSerializer
    permission_classes = [IsAuthenticated, IsComptable]


class CommandeViewSet(ModelViewSet):
    queryset = Commande.objects.all()
    serializer_class = CommandeSerializer
    permission_classes = [IsAuthenticated, IsComptable]

    def perform_create(self, serializer):
        if serializer.validated_data.get('quantite', 0) <= 0:
            raise serializers.ValidationError("La quantité doit être supérieure à 0.")
        serializer.save()


class LigneBudgetaireViewSet(ModelViewSet):
    queryset = LigneBudgetaire.objects.all()
    serializer_class = LigneBudgetaireSerializer
    permission_classes = [IsAuthenticated, IsComptable]

    def perform_create(self, serializer):
        ligne = serializer.save()
        budget = ligne.budget

        # Calcul de toutes les lignes existantes
        total_lignes = budget.lignes.aggregate(total=models.Sum('montant_alloue'))['total'] or 0
        total_apres = total_lignes
        verifier_ligne_budgetaire_autorisee(ligne.budget, ligne.montant_alloue)
        # Ajout de la ligne courante
        if total_apres > budget.montant_disponible:
            raise serializers.ValidationError(
                f"Montant alloué dépasse le budget disponible ({budget.montant_disponible} F)"
            )

        # Diminuer le budget disponible
        budget.montant_disponible -= ligne.montant_alloue
        budget.save()








class JournalAuditViewSet(ReadOnlyModelViewSet):
    queryset = JournalAudit.objects.all().order_by('-date_heure')
    serializer_class = JournalAuditSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend]
    filterset_class = JournalAuditFilter 





class RegisterView(APIView):
    permission_classes = [IsAuthenticated, IsComptable]

    @swagger_auto_schema(
        operation_description="Inscription d'un nouvel utilisateur (CSA ou Directeur uniquement par le Comptable)",
        request_body=RegisterSerializer,
        responses={201: openapi.Response('Utilisateur créé')}
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            utilisateur = serializer.save()
            return Response({'message': 'Utilisateur créé avec succès.'}, status=201)
        return Response(serializer.errors, status=400)




class ValidationDemandeDepenseView(APIView):
    permission_classes = [IsAuthenticated, IsDirecteur]

    @swagger_auto_schema(
        operation_description="Validation ou refus d'une demande de dépense par le Directeur",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'statut': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['approuvée', 'refusée'],
                    description="Statut final de la demande"
                ),
                'commentaire': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Commentaire du directeur (facultatif)"
                )
            },
            required=['statut']
        ),
        responses={200: openapi.Response('Demande traitée')}
    )
    def post(self, request, pk):
        try:
            demande = DemandeDepense.objects.get(pk=pk)
        except DemandeDepense.DoesNotExist:
            return Response({"error": "Demande introuvable."}, status=404)

        if demande.statut != 'en_attente':
            return Response({"error": "Demande déjà traitée."}, status=400)

        statut = request.data.get('statut')
        commentaire = request.data.get('commentaire', '')

        if statut not in ['approuvée', 'refusée']:
            return Response({"error": "Statut invalide."}, status=400)

        demande.statut = statut
        demande.commentaire_directeur = commentaire
        demande.date_validation = timezone.now()
        demande.save()

        return Response({"message": f"Demande {statut}."})




class RegisterView(APIView):
    permission_classes = [IsAuthenticated, IsComptable]

    @swagger_auto_schema(
        operation_description="Inscription d'un nouvel utilisateur",
        request_body=RegisterSerializer,
        responses={201: openapi.Response('Utilisateur créé')}
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            utilisateur = serializer.save()
            return Response({'message': 'Utilisateur créé avec succès.'}, status=201)
        return Response(serializer.errors, status=400)




class RapportFinancierViewSet(ModelViewSet):
    queryset = RapportFinancier.objects.all()
    serializer_class = RapportFinancierSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(genere_par=self.request.user)

    @action(detail=False, methods=['post'], url_path='generer')
    def generer_rapport(self, request):


        budget_id = request.data.get("budget_id")
        periode = request.data.get("periode", "Période non précisée")

        try:
            budget = Budget.objects.get(id=budget_id)
        except Budget.DoesNotExist:
            return Response({"error": "Budget introuvable."}, status=status.HTTP_404_NOT_FOUND)

        # Données à inclure dans le rapport
        recettes = Recette.objects.filter(budget=budget)
        depenses = Depense.objects.filter(budget=budget, statut_validation='validee')
        commandes = Commande.objects.filter(ligne_budgetaire__budget=budget)

        # Génération du fichier (ex: PDF ou Excel)
        rapport_file, filename = generate_rapport_file(budget, recettes, depenses, commandes, periode, request.user)

        # Sauvegarde dans le modèle
        rapport = RapportFinancier.objects.create(
            budget=budget,
            type='pdf',
            periode=periode,
            nom_fichier=filename,
            fichier=rapport_file,
            genere_par=request.user
        )

        return Response({"success": True, "message": "Rapport généré avec succès.", "rapport_id": rapport.id})


class TelechargerRapportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, rapport_id):
        try:
            rapport = RapportFinancier.objects.get(id=rapport_id)
        except RapportFinancier.DoesNotExist:
            return Response({"error": "Rapport introuvable."}, status=status.HTTP_404_NOT_FOUND)

        if not rapport.fichier:
            return Response({"error": "Aucun fichier généré pour ce rapport."}, status=status.HTTP_404_NOT_FOUND)

        return FileResponse(rapport.fichier, as_attachment=True, filename=rapport.nom_fichier)
