from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django.conf import settings
from django.utils.crypto import get_random_string

 
   # Manager personnalisé pour le modèle Utilisateur. Surcharge les méthodes de création d'user/superuser.

class UtilisateurManager(BaseUserManager):
    #Crée et enregistre un utilisateur standard.
    def create_user(self, email, nom, mot_de_passe=None, role="Comptable", **extra_fields):
            # Validation de l'email
        if not email:
            raise ValueError('L’utilisateur doit avoir un email')
             # Normalisation de l'email (minuscules, etc.)
        email = self.normalize_email(email)
                # Création de l'instance utilisateur
        user = self.model(email=email, nom=nom, role=role, **extra_fields)
        # Cryptage et sauvegarde du mot de passe
        user.set_password(mot_de_passe)
        user.save(using=self._db)
        return user
    
    
    # Crée et enregistre un superutilisateur (admin).
    def create_superuser(self, email, nom, mot_de_passe=None, **extra_fields):
           # Définition des attributs admin
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
         # Utilisation de la méthode create_user avec rôle Comptable par défaut
        return self.create_user(email, nom, mot_de_passe, role="Comptable", **extra_fields)

# Modèle personnalisé d'utilisateur qui remplace le modèle User par défaut de Django.
# Utilise l'email comme identifiant au lieu du username.

class Utilisateur(AbstractBaseUser, PermissionsMixin):
      # Choix possibles pour le rôle de l'utilisateur
    ROLE_CHOICES = [
        ('Comptable', 'Comptable'),
        ('Directeur', 'Directeur'),
        ('CSA', 'CSA'),
    ]

    email = models.EmailField(unique=True)
    nom = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Comptable')
    date_creation = models.DateTimeField(default=timezone.now)
       # Champs requis pour le modèle utilisateur Django
    is_active = models.BooleanField(default=True) # Compte activé
    is_staff = models.BooleanField(default=False) # Accès à l'admin


    # Configuration spécifique pour l'authentification
    USERNAME_FIELD = 'email' # Champ utilisé comme identifiant
    REQUIRED_FIELDS = ['nom'] # Champs requis pour createsuperuser

       # Lien vers le manager personnalisé
    objects = UtilisateurManager()

    def __str__(self):
        return f"{self.nom} ({self.role})"
    
    def est_comptable(self):
       return self.role == 'Comptable'

    def est_directeur(self):
       return self.role == 'Directeur'

    def est_csa(self):
       return self.role == 'CSA'





# 2 ===================== model budget =======================================
class Budget(models.Model):
    # Définition des statuts possibles pour un budget
    STATUT_CHOICES = [
        ('en_cours', 'En cours'),
        ('cloture', 'Clôturé'),
    ]
    

    # Champ pour l'année budgétaire (ex: "2023-2024")
    exercice = models.CharField(max_length=9, unique=True, verbose_name="Exercice budgétaire")  
     # Montant total alloué au budget
    montant_total = models.FloatField( verbose_name="Montant total alloué")


      # Statut courant du budget
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_cours',verbose_name="Statut du budget")
    # Date/heure de création (auto)
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
     # Date/heure de dernière modification (auto)
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")
       # Référence au comptable responsable
    comptable = models.ForeignKey('Utilisateur', on_delete=models.CASCADE, verbose_name="Comptable responsable")

    @property
    def montant_total_depenses_validees(self):
        return self.depenses.filter(statut_validation='validee').aggregate(total=Sum('montant'))['total'] or 0

    @property
    def montant_total_recettes(self):
        return self.recettes.aggregate(total=Sum('montant'))['total'] or 0

    @property
    def montant_disponible(self):
        return self.montant_total + self.montant_total_recettes - self.montant_total_depenses_validees

    def est_actif(self):
        return self.statut == 'en_cours'

    def __str__(self):
        return f"Budget {self.exercice} - {self.statut}"




# 3 ===================== model recette =======================================

class Recette(models.Model):
    # Clé étrangère vers le modèle Budget 
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='recettes', verbose_name="Budget associé")
    # Source de la recette (ex: "Subvention", "Droits d'inscription")
    source = models.CharField(max_length=100, verbose_name="Source de la recette")
     # Type de recette (ex: "Subvention", "Cotisation", "Don")
    type = models.CharField(max_length=50, verbose_name="Type de recette")
     # Montant de la recette
    montant = models.FloatField( verbose_name="Montant (FCFA)")
      # Date d'enregistrement de la recette
    date = models.DateField(verbose_name="Date de la recette")
       # Justificatif numérique (optionnel)
    justificatif = models.FileField(upload_to='justificatifs/recettes/', null=True, blank=True, verbose_name="Justificatif numérique")

    def __str__(self):
        return f"{self.source} - {self.montant} F"



# 4 ===================== model DemandeDepense =======================================

class DemandeDepense(models.Model):
    # Définition des statuts possibles pour une demande
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('approuvée', 'Approuvée'),
        ('refusée', 'Refusée'),
    ]
    # Lien vers l'utilisateur qui a fait la demande
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, verbose_name="Demandeur",related_name='demandes_depense')
      # Description détaillée de la demande   
    motif = models.TextField(verbose_name="Motif de la dépense",
        help_text="Décrivez en détail la nécessité de cette dépense")
     # Estimation du coût
    montant_estime = models.FloatField(verbose_name="Montant estimé (FCFA)",
        help_text="Estimation du coût en francs CFA")
     # Statut courant de la demande
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente', verbose_name="Statut de la demande")
     # Date de création automatique
    date_demande = models.DateField(auto_now_add=True, verbose_name="Date de la demande")
    # Date de validation (remplie lors de l'approbation/rejet)
    date_validation = models.DateField(null=True, blank=True, verbose_name="Date de validation")
     # Commentaires du directeur (optionnels)
    commentaire_directeur = models.TextField(blank=True, verbose_name="Commentaires du directeur",
        help_text="Commentaires éventuels sur la décision")

    def __str__(self):
        return f"Demande {self.id} - {self.statut}"

# ===================== model Commande =======================================
class LigneBudgetaire(models.Model):
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='lignes')
    article = models.CharField(max_length=100, verbose_name="Article ou poste budgétaire")
    montant_alloue = models.FloatField(verbose_name="Montant alloué à cette ligne")

    def __str__(self):
        return f"{self.article} - {self.montant_alloue} F"




# 6 ===================== model Fournisseur =======================================

class Fournisseur(models.Model):
    # Nom complet du fournisseur
    nom = models.CharField(max_length=100, verbose_name="Nom du fournisseur",
        help_text="Nom complet ou raison sociale")
    # Type de fournisseur (ex: "Matériel", "Service", "Consultant")
    type = models.CharField(max_length=50, verbose_name="Type de fournisseur",
        help_text="Catégorie principale d'activité" )
    # Adresse postale complète
    adresse = models.TextField(verbose_name="Adresse complète",
        help_text="Adresse postale avec ville et pays")
     # Email de contact (validation automatique du format)
    email = models.EmailField(verbose_name="Adresse complète",
        help_text="Adresse postale avec ville et pays")
    # Numéro de téléphone (format flexible)
    telephone = models.CharField(max_length=20, verbose_name="Téléphone",
        help_text="Numéro avec indicatif (ex: +221 XXX XX XX)")
       # Numéro de Registre du Commerce
    numero_rc = models.CharField(max_length=50, verbose_name="Numéro RC",
        help_text="Numéro d'inscription au registre du commerce")
      # Numéro d'identification fiscale (NINEA)
    ninea = models.CharField(max_length=50, verbose_name="NINEA",
        help_text="Numéro d'Identification national des Entreprises et Associations",unique=True)

    def __str__(self):
        return self.nom

# ===================== model commande =======================================
class Commande(models.Model):
        ligne_budgetaire = models.ForeignKey(LigneBudgetaire, on_delete=models.CASCADE, related_name='commandes')
        fournisseur = models.ForeignKey(Fournisseur, on_delete=models.CASCADE)
        reference = models.CharField(max_length=50)
        date = models.DateField()

        # Champs intégrés (au lieu de LigneCommande)
        designation = models.CharField(max_length=100, verbose_name="Désignation")
        quantite = models.PositiveIntegerField(default=1)
        prix_unitaire = models.FloatField()

        total = models.FloatField(blank=True, null=True)

        STATUT_CHOICES = [
            ('en_attente', 'En attente'),
            ('validee', 'Validée'),
            ('rejettee', 'Rejetée'),
        ]
        statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')

        def save(self, *args, **kwargs):
            self.total = self.quantite * self.prix_unitaire
            super().save(*args, **kwargs)

        def __str__(self):
            return f"{self.reference} - {self.designation}"

# 5 ===================== model Depense =======================================

class Depense(models.Model):
      # Lien vers le budget concerné (obligatoire)
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE,verbose_name="Budget associé",
        related_name='depenses')

    ligne_budgetaire = models.ForeignKey(LigneBudgetaire, on_delete=models.CASCADE, related_name='depenses')
    commande = models.ForeignKey(Commande, on_delete=models.SET_NULL, null=True, blank=True, related_name='depenses')
      # Lien optionnel vers une demande préalable
    demande = models.ForeignKey(DemandeDepense, on_delete=models.SET_NULL, null=True, blank=True, 
    verbose_name="Demande associée", help_text="Lien vers la demande préalable (si existante)")
    #
    est_planifiee = models.BooleanField(default=False)

    supervise_par = models.ForeignKey(
    Utilisateur, on_delete=models.SET_NULL, null=True, blank=True, related_name='depenses_supervisees'
)
  
    valide_par = models.ForeignKey(Utilisateur, on_delete=models.SET_NULL, null=True, blank=True, related_name='depenses_validees')
    
    statut_validation = models.CharField(max_length=20, choices=[
        ('en_attente', 'En attente'),
        ('validee', 'Validée'),
        ('rejetee', 'Rejetée')
    ], default='en_attente')

    date_validation = models.DateField(null=True, blank=True)

     # Date réelle de la dépense
    date = models.DateField(verbose_name="Date d'engagement", help_text="Date effective de la dépense")
     # Montant réel dépensé
    montant = models.FloatField(verbose_name="Montant (FCFA)", help_text="Montant effectivement dépensé")
     # Description détaillée
    description = models.TextField(verbose_name="Description", help_text="Détails sur la nature de la dépense")
    # Type de dépense (ex: "Achat fournitures", "Frais de mission")
    type_depense = models.CharField(max_length=100, verbose_name="Type de dépense")
     # Catégorie budgétaire (ex: "Fonctionnement", "Investissement")
    categorie = models.CharField(max_length=50, verbose_name="Catégorie budgétaire")
    # Pièce justificative numérique
    justificatif = models.FileField(upload_to='justificatifs/depenses/', null=True, blank=True, 
     verbose_name="Pièce justificative", help_text="Document PDF/Image attestant la dépense")

    def __str__(self):
        return f"{self.type_depense} - {self.montant} F"











# 9 ==================== rapport financier =======================================

class RapportFinancier(models.Model):
    TYPE_CHOICES = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
    ]

    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='rapports',
        verbose_name="Budget associé")
     # Format du rapport (choix limité)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, verbose_name="Format du rapport",
        help_text="Type de fichier généré")
    # Période couverte par le rapport
    periode = models.CharField(max_length=20,  verbose_name="Période couverte",
        help_text="Ex: 'T1 2024', 'Janvier - Mars 2024'") 
     # Nom original du fichier (sans le chemin)
    nom_fichier = models.CharField(max_length=255, verbose_name="Nom du fichier",
        help_text="Nom original du rapport")
     # Fichier stocké physiquement
    fichier = models.FileField(upload_to='rapports/',  verbose_name="Fichier du rapport",
        help_text="Fichier PDF ou Excel généré", null=True, blank=True)
    # Date/heure de création automatique
    date_generation = models.DateTimeField(auto_now_add=True, verbose_name="Date de génération"
)
    # Utilisateur ayant généré le rapport
    genere_par = models.ForeignKey(Utilisateur, on_delete=models.SET_NULL, null=True,
      verbose_name="Généré par", help_text="Responsable de la génération")

    def __str__(self):
        return f"{self.periode} - {self.type.upper()}"






class JournalAudit(models.Model):
    """
    Journalisation des actions critiques effectuées par les utilisateurs
    """
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.SET_NULL, null=True)
    action = models.TextField()
    date_heure = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.utilisateur} - {self.action[:40]}..."




class Code2FA(models.Model):
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    date_envoi = models.DateTimeField(auto_now_add=True)
    est_utilise = models.BooleanField(default=False)

    def est_expire(self):
        return timezone.now() > self.date_envoi + timezone.timedelta(minutes=10)

    def __str__(self):
        return f"Code 2FA pour {self.utilisateur.email} - {self.code}"




from django.contrib.auth import get_user_model

Utilisateur = get_user_model()

class Notification(models.Model):

        NIVEAU_CHOICES = [
            ('info', 'Info'),
            ('alerte', 'Alerte'),
        ]

        utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='notifications')
        message = models.CharField(max_length=255)
        url = models.CharField(max_length=255, blank=True, null=True)
        niveau = models.CharField(max_length=10, choices=NIVEAU_CHOICES, default='info')
        lu = models.BooleanField(default=False)
        date_creation = models.DateTimeField(auto_now_add=True)

        class Meta:
            ordering = ['-date_creation']

        def __str__(self):
            return f"Notification pour {self.utilisateur.nom} - {'Lu' if self.lu else 'Non lu'}"

