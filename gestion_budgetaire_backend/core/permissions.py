# core/permissions.py

from rest_framework.permissions import BasePermission

# Permission pour le Comptable
class IsComptable(BasePermission):
    """
    Autorise uniquement les utilisateurs avec le rôle 'Comptable'
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'Comptable'


# Permission pour le Directeur
class IsDirecteur(BasePermission):
    """
    Autorise uniquement les utilisateurs avec le rôle 'Directeur'
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'Directeur'


# Permission pour le CSA
class IsCSA(BasePermission):
    """
    Autorise uniquement les utilisateurs avec le rôle 'CSA'
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'CSA'


class Is2FAVerified(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_verified_2fa