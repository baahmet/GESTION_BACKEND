# core/urls.py

from .views import TelechargerRapportView, MeView, UpdateMyAccountView, NotificationListView, marquer_notification_lue, \
    ValidationDemandeDepenseView, marquer_toutes_notifications_lues

from .auth_2fa import Resend2FACodeView, CustomLoginView, Validate2FACodeView
from .views import ValidationCommandeView

from rest_framework.permissions import AllowAny
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    BudgetViewSet, RecetteViewSet, DemandeDepenseViewSet,
    DepenseViewSet, FournisseurViewSet, CommandeViewSet,
    LigneBudgetaireViewSet, RapportFinancierViewSet,
    ValidationDepenseView, SupervisionDepenseView, JournalAuditViewSet,UtilisateurViewSet,RegisterView
)

router = DefaultRouter()
router.register('utilisateurs', UtilisateurViewSet)
router.register('budgets', BudgetViewSet)
router.register('recettes', RecetteViewSet)
router.register('demandes', DemandeDepenseViewSet)
router.register('depenses', DepenseViewSet)
router.register('fournisseurs', FournisseurViewSet)
router.register('commandes', CommandeViewSet)
router.register('lignes', LigneBudgetaireViewSet)
router.register('rapports', RapportFinancierViewSet)
router.register('journal', JournalAuditViewSet)
router.register(r'rapports', RapportFinancierViewSet, basename='rapport')


schema_view = get_schema_view(
    openapi.Info(
        title="API Budget UFR SET",
        default_version='v1',
        description="Documentation interactive de l’API",
    ),
    public=True,
    permission_classes=(AllowAny,),
)

urlpatterns = [
    # Routes JWT en PREMIER (avant le routeur)
   # path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Route d'enregistrement
    path('register/', RegisterView.as_view(), name='register'),
    
    # Documentation Swagger
    path('docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    
    # Routes du routeur (API CRUD)
    path('', include(router.urls)),
    
    # Routes personnalisées
    path('depenses/<int:pk>/superviser/', SupervisionDepenseView.as_view(), name='supervision-depense'),
    path('depenses/<int:pk>/valider/', ValidationDepenseView.as_view(), name='validation-depense'),
    path('commandes/<int:pk>/valider/', ValidationCommandeView.as_view(), name='validation-commande'),
    path('demandes/<int:pk>/valider/', ValidationDemandeDepenseView.as_view(), name='valider_demande_depense'),
    path('2fa/resend/', Resend2FACodeView.as_view(), name='resend-2fa'),
    path('login/', CustomLoginView.as_view(), name='custom-login'),
    path('login/2fa/', Validate2FACodeView.as_view(), name='validate-2fa'),

    path('rapports/<int:rapport_id>/telecharger/', TelechargerRapportView.as_view(), name='telecharger-rapport'),


    path('me/', MeView.as_view()),
    path('me/update/', UpdateMyAccountView.as_view()),

    path('notifications/', NotificationListView.as_view(), name='notifications-list'),
    path('notifications/<int:pk>/marquer_lue/', marquer_notification_lue, name='notifications-mark-read'),
    path('notifications/marquer_toutes_lues/', marquer_toutes_notifications_lues, name='notifications-mark-all-read'),

]



