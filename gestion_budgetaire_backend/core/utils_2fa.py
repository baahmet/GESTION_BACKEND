# core/utils_2fa.py

from django.core.mail import send_mail

def envoyer_code_verification(email, nom, code):
    sujet = "Code de vérification de votre compte"
    message = f"""
    Bonjour {nom},

    Voici votre code de vérification pour activer votre compte :

    ✅ Code : {code}

    Merci de le saisir dans l'application pour activer votre accès.

    -- Système de gestion budgétaire UFR SET
    """
    send_mail(
        sujet,
        message,
        "baahmet126@gmail.com",  # 👉 Ton adresse d'envoi
        [email],
        fail_silently=False,
    )
