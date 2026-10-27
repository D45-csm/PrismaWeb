from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.

class Usuario(AbstractUser):
    telefono = models.CharField(max_length=10, null=False, blank=False)
    recovery_code_hash = models.CharField(max_length=128, blank=True, default='')
    email_recovery_code_hash = models.CharField(max_length=128, blank=True, default='')
    email_recovery_code_expires_at = models.DateTimeField(blank=True, null=True)
    recovery_code_attempts = models.PositiveSmallIntegerField(default=0)
    recovery_code_locked_until = models.DateTimeField(blank=True, null=True)
    recovery_reset_grant_hash = models.CharField(max_length=128, blank=True, default='')
    recovery_reset_grant_expires_at = models.DateTimeField(blank=True, null=True)