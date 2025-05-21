from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string
from core.models import Utilisateur
from core.utils_2fa import envoyer_code_verification

class Command(BaseCommand):
    help = 'Régénère et envoie un code 2FA à tous les utilisateurs'

    def handle(self, *args, **kwargs):
        utilisateurs = Utilisateur.objects.all()
        for user in utilisateurs:
            code = get_random_string(length=6, allowed_chars='0123456789')
            user.code_verification = code
            user.is_verified_2fa = False
            user.save()

            envoyer_code_verification(user.email, user.nom, code)

            self.stdout.write(self.style.SUCCESS(f"✅ Code 2FA envoyé à {user.email}"))
