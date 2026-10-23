from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from config.validators import validate_image_upload


class Profile(models.Model):
    ROLE_USER = 'USER'
    ROLE_ADMIN = 'ADMIN'

    ROLE_CHOICES = [
        (ROLE_USER, 'User'),
        (ROLE_ADMIN, 'Administrator'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_USER)
    profile_image = models.ImageField(
        upload_to='profile_images/', blank=True, null=True,
        validators=[validate_image_upload],
    )
    phone = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} — {self.get_role_display()}"

    def is_admin(self):
        return self.role == self.ROLE_ADMIN or self.user.is_superuser

    class Meta:
        verbose_name = 'Profile'
        verbose_name_plural = 'Profiles'


class LoginAttempt(models.Model):
    """Recent failed-login counter event keyed by a secret-derived username hash."""

    subject_hash = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['subject_hash', 'created_at'])]


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Auto-create or update Profile whenever a User is saved."""
    if created:
        role = Profile.ROLE_ADMIN if instance.is_superuser else Profile.ROLE_USER
        Profile.objects.create(user=instance, role=role)
    else:
        # If profile exists, sync role for superusers
        if hasattr(instance, 'profile'):
            if instance.is_superuser and instance.profile.role != Profile.ROLE_ADMIN:
                instance.profile.role = Profile.ROLE_ADMIN
                instance.profile.save()
        else:
            role = Profile.ROLE_ADMIN if instance.is_superuser else Profile.ROLE_USER
            Profile.objects.create(user=instance, role=role)
