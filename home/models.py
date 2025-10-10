from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db.models.signals import post_save
from django.dispatch import receiver

# ========== Custom User Manager ==========
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)

# ========== Custom User Model ==========
class CustomUser(AbstractUser):
    username = None
    email = models.EmailField(unique=True)

    class UserType(models.TextChoices):
        FREELANCER = 'freelancer', 'Freelancer'
        ORGANIZATION = 'organization', 'Organization'

    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.FREELANCER
    )

    objects = CustomUserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"{self.email} ({self.get_user_type_display()})"

# ========== Tag Model (Used for Skills) ==========
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

# ========== Post Model ==========
class Post(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="posts")
    title = models.CharField(max_length=255, default="Untitled Post")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} by {self.user.email}"

    class Meta:
        ordering = ['-created_at']

# ========== Experience for Freelancers ==========
class Experience(models.Model):
    profile = models.ForeignKey("Profile", on_delete=models.CASCADE, related_name="experiences")
    organization = models.CharField(max_length=255)
    role = models.CharField(max_length=255)
    years = models.DecimalField(max_digits=4, decimal_places=1)  # 1.5 years, 2.0 etc.
    details = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.role} at {self.organization}"

# ========== Profile Model ==========
class Profile(models.Model):
    # Shared Fields
    profile_picture = models.ImageField(upload_to="profile_pictures/", blank=True, null=True)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="profile")
    bio = models.TextField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    industry = models.CharField(max_length=255, blank=True, null=True)

    # Freelancer-specific
    social_links = models.JSONField(blank=True, null=True)
    skills = models.ManyToManyField(Tag, blank=True)

    # Organization-specific
    company_name = models.CharField(max_length=255, blank=True, null=True)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)

    def __str__(self):
        return f"Profile of {self.user.email}"

# ========== Network / Connections ==========
class Connection(models.Model):
    user = models.ForeignKey(CustomUser, related_name="following", on_delete=models.CASCADE)
    connected_to = models.ForeignKey(CustomUser, related_name="followers", on_delete=models.CASCADE)
    connected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'connected_to')

    def __str__(self):
        return f"{self.user.email} connected with {self.connected_to.email}"

class Project(models.Model):
    class StatusChoices(models.TextChoices):
        ONGOING = "ongoing", "Ongoing"
        COMPLETED = "completed", "Completed"

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='projects', null=True)
    project_description = models.TextField()
    required_skills = models.ManyToManyField(Tag, blank=True)
    terms_of_contract = models.TextField()
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ONGOING)
    collaborators = models.ManyToManyField(CustomUser, blank=True, limit_choices_to={"user_type": "freelancer"})

    def __str__(self):
        return f"Project for {self.profile.company_name or self.profile.user.email}"


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created and not hasattr(instance, 'profile'):
        Profile.objects.create(user=instance)

class MatchRequest(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    freelancer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'freelancer'},
        related_name='sent_match_requests'
    )
    project = models.ForeignKey(
        "Project",
        on_delete=models.CASCADE,
        related_name='match_requests'
    )
    status = models.CharField(
        max_length=10,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('freelancer', 'project')  # Prevent duplicate requests

    def __str__(self):
        return f"{self.freelancer.email} → {self.project.profile.company_name} ({self.status})"
