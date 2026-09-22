from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.

class Usuario(AbstractUser):
    telefono = models.CharField(max_length=10, null=False, blank=False)