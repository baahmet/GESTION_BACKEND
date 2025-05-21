from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import serializers
from .models import Code2FA, Utilisateur
from django.utils.crypto import get_random_string
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .utils_2fa import envoyer_code_verification
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone

# 1 Étape 1 : login (email + mot de passe)
class CustomLoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        utilisateur = Utilisateur.objects.filter(email=email).first()

        if not utilisateur or not utilisateur.check_password(password):
            raise serializers.ValidationError("Identifiants invalides")

        # 🔐 Génération du code 2FA
        code = get_random_string(6, allowed_chars='0123456789')
        Code2FA.objects.create(utilisateur=utilisateur, code=code)

        envoyer_code_verification(utilisateur.email, utilisateur.nom, code)

        return {
            "message": "Code 2FA envoyé. Veuillez le valider pour obtenir votre token.",
            "email": utilisateur.email
        }

class CustomLoginView(TokenObtainPairView):
    serializer_class = CustomLoginSerializer
    permission_classes = [AllowAny]

# 2 Étape 2 : vérification du code
class Validate2FACodeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        code = request.data.get("code")

        try:
            utilisateur = Utilisateur.objects.get(email=email)
        except Utilisateur.DoesNotExist:
            return Response({"error": "Utilisateur introuvable"}, status=404)

        try:
            code_obj = Code2FA.objects.filter(
                utilisateur=utilisateur,
                code=code,
                est_utilise=False
            ).order_by('-date_envoi').first()
            if not code_obj:
                return Response({"error": "Code incorrect ou expiré."}, status=400)
        except Code2FA.DoesNotExist:
            return Response({"error": "Aucun code actif trouvé."}, status=400)

        if code_obj.est_expire():
            return Response({"error": "Code expiré"}, status=400)

        # Marquer comme utilisé
        code_obj.est_utilise = True
        code_obj.save()

        # Générer les tokens
        refresh = RefreshToken.for_user(utilisateur)

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "email": utilisateur.email,
                "nom": utilisateur.nom,
                "role": utilisateur.role
            }
        })

# 3 Resend code si l’utilisateur ne l’a pas reçu
class Resend2FACodeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')

        try:
            utilisateur = Utilisateur.objects.get(email=email)
        except Utilisateur.DoesNotExist:
            return Response({"error": "Utilisateur introuvable."}, status=404)

        # Génération d’un nouveau code
        code = get_random_string(6, allowed_chars='0123456789')
        Code2FA.objects.create(utilisateur=utilisateur, code=code, date_envoi=timezone.now())

        envoyer_code_verification(utilisateur.email, utilisateur.nom, code)

        return Response({"message": "Nouveau code envoyé avec succès."})
