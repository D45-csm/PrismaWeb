from django.db import models
from insumos.models import Insumo

class Receta(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    # insumo se relaciona directamente con receta, creando una tabla intermedia 
    insumos = models.ManyToManyField(Insumo, through='RecetaInsumo')

    def __str__(self):
        return self.nombre

# relaciona la linea entre un insumo y una receta, indicando la cantidad y la medida del insumo en la receta
class RecetaInsumo(models.Model):
    unidad_medida_choices = [
        ('g', 'Gramo'),
        ('ml', 'Mililitro'),
        ('kg', 'Kilogramo'),
        ('l', 'Litro'),
        ('u', 'Unidad'),
    ]

    receta = models.ForeignKey(Receta, on_delete=models.CASCADE)
    insumo = models.ForeignKey(Insumo, on_delete=models.CASCADE)
    cantidad_insumo = models.FloatField()
    medida_insumo = models.CharField(max_length=20, choices=unidad_medida_choices)

    def __str__(self):
        return f"{self.cantidad_insumo}{self.medida_insumo} de {self.insumo.nombre} para {self.receta.nombre}"