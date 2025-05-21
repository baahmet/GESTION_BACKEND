from django.http import FileResponse
from django.utils import timezone
from django.db import models
from rest_framework import serializers, status, generics, permissions
from rest_framework.decorators import action, permission_classes, api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from .filters import JournalAuditFilter
from .models import (
    Budget, Recette, Depense, DemandeDepense,
    Fournisseur, Commande, LigneBudgetaire, RapportFinancier, Utilisateur, JournalAudit, Notification
)
from .notifications import NotificationService

from .serializers import (
    BudgetSerializer, RecetteSerializer, DepenseSerializer,
    DemandeDepenseSerializer, FournisseurSerializer,
    CommandeSerializer, LigneBudgetaireSerializer,
    RapportFinancierSerializer, UtilisateurSerializer,
    JournalAuditSerializer, RegisterSerializer, UpdateMyAccountSerializer, NotificationSerializer
)

from .permissions import IsComptable, IsDirecteur, IsCSA
from .utils.rapport_generator import generate_rapport_file
from .utils_validations import verifier_ligne_budgetaire_autorisee, verifier_depense_autorisee, verifier_commande_autorisee

# Utilisateurs (lecture seule par tous authentifiés)
class UtilisateurViewSet(ReadOnlyModelViewSet):
    queryset = Utilisateur.objects.all()
    serializer_class = UtilisateurSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy', 'create']:
            return [IsAuthenticated(), IsComptable()]
        return [IsAuthenticated()]

# Budget (CRUD : Comptable / GET : Directeur & CSA)
class BudgetViewSet(ModelViewSet):
    queryset = Budget.objects.all()
    serializer_class = BudgetSerializer

    def get_permissions(self):
        if self.request.method in ['GET', 'HEAD', 'OPTIONS']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsComptable()]


#  Recette (CRUD : Comptable / GET : Directeur & CSA)
class RecetteViewSet(ModelViewSet):
    queryset = Recette.objects.all()
    serializer_class = RecetteSerializer

    def get_permissions(self):
        if self.request.method in ['GET', 'HEAD', 'OPTIONS']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsComptable()]

    def perform_create(self, serializer):
        serializer.save()



# Dépenses (CRUD : Comptable / GET : Directeur & CSA)
class DepenseViewSet(ModelViewSet):
    queryset = Depense.objects.all()
    serializer_class = DepenseSerializer

    def get_permissions(self):
        if self.request.method in ['GET', 'HEAD', 'OPTIONS']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsComptable()]

    def perform_create(self, serializer):
        budget = serializer.validated_data['budget']
        if budget.statut == 'cloture':
            raise serializers.ValidationError("Ce budget est clôturé.")
        serializer.save()

        NotificationService.notify_roles(
            roles="CSA",
            message=f"🧾 Dépense soumise par {self.request.user.nom}"
        )


# Fournisseurs (CRUD : Comptable / GET : Directeur & CSA)
class FournisseurViewSet(ModelViewSet):
    queryset = Fournisseur.objects.all()
    serializer_class = FournisseurSerializer

    def get_permissions(self):
        if self.request.method in ['GET', 'HEAD', 'OPTIONS']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsComptable()]


#  Commandes (CRUD : Comptable / GET : Directeur & CSA)
class CommandeViewSet(ModelViewSet):
    queryset = Commande.objects.all()
    serializer_class = CommandeSerializer

    def get_permissions(self):
        if self.request.method in ['GET', 'HEAD', 'OPTIONS']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsComptable()]

    def perform_create(self, serializer):
        if serializer.validated_data.get('quantite', 0) <= 0:
            raise serializers.ValidationError("La quantité doit être > 0.")
        serializer.save()


# Lignes budgétaires (CRUD : Comptable / GET : Directeur & CSA)
class LigneBudgetaireViewSet(ModelViewSet):
    queryset = LigneBudgetaire.objects.all()
    serializer_class = LigneBudgetaireSerializer

    def get_permissions(self):
        if self.request.method in ['GET', 'HEAD', 'OPTIONS']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsComptable()]




#  Demande de dépense (lecture & création libre)
class DemandeDepenseViewSet(ModelViewSet):
    queryset = DemandeDepense.objects.all()
    serializer_class = DemandeDepenseSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(utilisateur=self.request.user)
        NotificationService.notify_roles(
            roles="Directeur",
            message=f"📩 Nouvelle demande de dépense soumise par {self.request.user.nom}")


#  Journal d'audit (lecture seule)
class JournalAuditViewSet(ReadOnlyModelViewSet):
    queryset = JournalAudit.objects.all().order_by('-date_heure')
    serializer_class = JournalAuditSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = JournalAuditFilter


#  Supervision d'une dépense (CSA uniquement)
class SupervisionDepenseView(APIView):
    permission_classes = [IsAuthenticated, IsCSA]

    @swagger_auto_schema(
        operation_description="Supervision d’une dépense par le CSA",
        responses={200: openapi.Response('Dépense supervisée')}
    )
    def post(self, request, pk):
        try:
            depense = Depense.objects.get(pk=pk)
        except Depense.DoesNotExist:
            return Response({"error": "Dépense introuvable."}, status=404)

        if depense.supervise_par:
            return Response({"error": "Cette dépense est déjà supervisée."}, status=400)

        if depense.statut_validation != 'en_attente':
            return Response({"error": "Impossible de superviser une dépense déjà traitée."}, status=400)

        depense.supervise_par = request.user
        depense.save()

        NotificationService.notify_roles(
            roles="Directeur",
            message=f"🔍 Dépense {depense.type_depense} supervisée par {request.user.nom}"
        )
        return Response({"message": "Supervision effectuée avec succès."})


#  Validation dépense (Directeur uniquement)
class ValidationDepenseView(APIView):
    permission_classes = [IsAuthenticated, IsDirecteur]

    def post(self, request, pk):
        try:
            depense = Depense.objects.get(pk=pk)
        except Depense.DoesNotExist:
            return Response({"error": "Dépense introuvable."}, status=404)

        if depense.statut_validation != 'en_attente':
            return Response({"error": "Déjà traitée."}, status=400)

        if not depense.supervise_par:
            return Response({"error": "La dépense doit être supervisée."}, status=403)

        action = request.data.get("statut_validation")
        if action not in ['validee', 'rejettee']:
            return Response({"error": "Statut non valide."}, status=400)

        depense.statut_validation = action
        depense.valide_par = request.user
        depense.date_validation = timezone.now()
        depense.save()

        if action == 'validee':
            if depense.montant > depense.budget.montant_disponible:
                return Response({"error": "Fonds insuffisants."}, status=400)
            NotificationService.notify_roles(
                roles="Comptable",
                message=f"✅ Dépense validée par {request.user.nom}"
            )



        JournalAudit.objects.create(
            utilisateur=request.user,
            action=f"Dépense {depense.type} {action.upper()} - {depense.montant} F"
        )

        return Response({"message": f"Dépense {action}."})


class ValidationDemandeDepenseView(APIView):
    permission_classes = [IsAuthenticated, IsDirecteur]

    @swagger_auto_schema(
        operation_description="Valider ou refuser une demande de dépense",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'statut': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['approuvée', 'refusée'],
                    description="Statut final de la demande"
                )
            },
            required=['statut']
        ),
        responses={200: openapi.Response('Demande validée ou refusée')}
    )
    def post(self, request, pk):
        try:
            demande = DemandeDepense.objects.get(pk=pk)
        except DemandeDepense.DoesNotExist:
            return Response({"error": "Demande introuvable."}, status=404)

        if demande.statut != 'en_attente':
            return Response({"error": "Cette demande a déjà été traitée."}, status=400)

        statut = request.data.get("statut")
        if statut not in ['approuvée', 'refusée']:
            return Response({"error": "Statut non valide."}, status=400)

        demande.statut = statut
        demande.save()

        # 🔔 Notifier Comptable si approuvée
        if statut == 'approuvée':
            NotificationService.notify_roles(
                roles="Comptable",
                message=f"✅ Demande {demande.motif} approuvée par {request.user.nom}"
            )

        # 🔔 Journalisation (optionnel)
        JournalAudit.objects.create(
            utilisateur=request.user,
            action=f"Demande de dépense {demande.motif} {statut.upper()}",
            date_heure=timezone.now()
        )

        return Response({"message": f"Demande {statut}."})





# Validation Commande (Comptable uniquement)
class ValidationCommandeView(APIView):
    permission_classes = [IsAuthenticated, IsComptable]

    @swagger_auto_schema(
        operation_description="Valider ou rejeter une commande",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={'statut': openapi.Schema(type=openapi.TYPE_STRING, enum=['validee', 'rejettee'])},
            required=['statut']
        )
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
                return Response({"error": "Dépassement de la ligne budgétaire."}, status=400)
            ligne.montant_alloue -= montant
            ligne.save()

        commande.statut = action
        commande.save()

        JournalAudit.objects.create(
            utilisateur=request.user,
            action=f"Commande {commande.reference} {action.upper()} - {montant} F",
            date_heure=timezone.now()
        )

        return Response({"message": f"Commande {action}."})




#  Register Utilisateur (Comptable uniquement)
class RegisterView(APIView):
    permission_classes = [IsAuthenticated, IsComptable]

    @swagger_auto_schema(
        operation_description="Création d'un nouvel utilisateur",
        request_body=RegisterSerializer,
        responses={201: openapi.Response('Utilisateur créé')}
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            utilisateur = serializer.save()
            return Response({'message': 'Utilisateur créé avec succès.'}, status=201)
        return Response(serializer.errors, status=400)


# Rapport Financier (lecture / création)
class RapportFinancierViewSet(ModelViewSet):
    queryset = RapportFinancier.objects.all()
    serializer_class = RapportFinancierSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(genere_par=self.request.user)

    @action(detail=False, methods=['post'], url_path='generer')
    def generer_rapport(self, request):
        budget_id = request.data.get("budget")

        periode = request.data.get("periode", "Période non précisée")

        try:
            budget = Budget.objects.get(id=budget_id)
        except Budget.DoesNotExist:
            return Response({"error": "Budget introuvable."}, status=status.HTTP_404_NOT_FOUND)

        recettes = Recette.objects.filter(budget=budget)
        depenses = Depense.objects.filter(budget=budget, statut_validation='validee')
        commandes = Commande.objects.filter(ligne_budgetaire__budget=budget)

        rapport_file, filename = generate_rapport_file(budget, recettes, depenses, commandes, periode, request.user)

        rapport = RapportFinancier.objects.create(
            budget=budget,
            type='pdf',
            periode=periode,
            nom_fichier=filename,
            fichier=rapport_file,
            genere_par=request.user
        )

        serializer = self.get_serializer(rapport)
        return Response({
            "success": True,
            "message": "Rapport généré avec succès.",
            "rapport": serializer.data
        })
# Télécharger un rapport (tout utilisateur connecté)
class TelechargerRapportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, rapport_id):
        try:
            rapport = RapportFinancier.objects.get(id=rapport_id)
        except RapportFinancier.DoesNotExist:
            return Response({"error": "Rapport introuvable."}, status=status.HTTP_404_NOT_FOUND)

        if not rapport.fichier:
            return Response({"error": "Aucun fichier généré."}, status=status.HTTP_404_NOT_FOUND)

        return FileResponse(rapport.fichier, as_attachment=True, filename=rapport.nom_fichier)




class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UtilisateurSerializer(request.user)
        return Response(serializer.data)

class UpdateMyAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = UpdateMyAccountSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"success": True, "message": "Compte mis à jour."})
        return Response(serializer.errors, status=400)








# Notifications
class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Retourne les notifications du user connecté, triées par date décroissante
        return Notification.objects.filter(utilisateur=self.request.user).order_by('-date_creation')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def marquer_notification_lue(request, pk):
    try:
        notification = Notification.objects.get(pk=pk, utilisateur=request.user)
    except Notification.DoesNotExist:
        return Response({"error": "Notification non trouvée."}, status=status.HTTP_404_NOT_FOUND)

    notification.lu = True
    notification.save()
    return Response({"message": "Notification marquée comme lue."})



@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def marquer_toutes_notifications_lues(request):
    notifications = Notification.objects.filter(utilisateur=request.user, lu=False)
    updated = notifications.update(lu=True)
    return Response({"message": f"{updated} notifications marquées comme lues."})
