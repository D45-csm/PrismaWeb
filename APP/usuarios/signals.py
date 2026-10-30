from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import EstadoRol


@receiver(post_save, sender=Group)
def crear_estado_rol(sender, instance, created, **kwargs):
    if created:
        EstadoRol.objects.get_or_create(group=instance)
