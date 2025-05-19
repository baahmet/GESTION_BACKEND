# core/permissions.py

from rest_framework.permissions import BasePermission

class IsComptable(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'Comptable'

class IsDirecteur(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'Directeur'

class IsCSA(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'CSA'

class IsReadOnly(BasePermission):
    """
    Autorise lecture seule (GET, HEAD, OPTIONS)
    """
    def has_permission(self, request, view):
         return request.user.is_authenticated and request.method in ['GET', 'HEAD', 'OPTIONS']




class Is2FAVerified(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_verified_2fa