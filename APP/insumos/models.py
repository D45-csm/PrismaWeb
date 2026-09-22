from django.db import models

# Create your models here.
class CategoriaInsumo(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

class Insumo(models.Model):
    unidad_medida_choices = [
        ('g', 'Gramo'),
        ('ml', 'Mililitro'),
        ('kg', 'Kilogramo'),
        ('l', 'Litro'),
        ('u', 'Unidad'),
    ]

    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    unidad_medida= models.CharField(max_length=20, choices=unidad_medida_choices)
    categoria = models.ForeignKey(CategoriaInsumo, on_delete=models.CASCADE)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre