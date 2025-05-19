# utils/notification_service.py

from .models import Utilisateur, Notification

class NotificationService:

    @classmethod
    def notify_roles(cls, roles, message, niveau="info"):
        """
        Envoie une notification à tous les utilisateurs ayant un rôle donné.
        roles: str ou list de rôles ('Comptable', 'Directeur', etc.)
        message: contenu de la notification
        niveau: niveau d'alerte ('info', 'alerte', etc.)
        """
        if isinstance(roles, str):
            roles = [roles]

        utilisateurs = Utilisateur.objects.filter(role__in=roles)
        for user in utilisateurs:
            Notification.objects.create(
                utilisateur=user,
                message=message,
                niveau=niveau
            )

    @classmethod
    def notify_user(cls, utilisateur, message, niveau="info"):
        """
        Envoie une notification à un seul utilisateur
        """
        Notification.objects.create(
            utilisateur=utilisateur,
            message=message,
            niveau=niveau
        )
