from django.db import models
from django.contrib.auth.models import AbstractUser, Group
# Create your models here.


class EstadoRol(models.Model):
    group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        related_name='estado_rol',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'estado de rol'
        verbose_name_plural = 'estados de roles'


class Usuario(AbstractUser):
    telefono = models.CharField(max_length=10, null=False, blank=False)
    recovery_code_hash = models.CharField(max_length=128, blank=True, default='')
    email_recovery_code_hash = models.CharField(max_length=128, blank=True, default='')
    email_recovery_code_expires_at = models.DateTimeField(blank=True, null=True)
    admin_recovery_code_sent_at = models.DateTimeField(blank=True, null=True)
    recovery_code_attempts = models.PositiveSmallIntegerField(default=0)
    recovery_code_locked_until = models.DateTimeField(blank=True, null=True)
    recovery_reset_grant_hash = models.CharField(max_length=128, blank=True, default='')
    recovery_reset_grant_expires_at = models.DateTimeField(blank=True, null=True)