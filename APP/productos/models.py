from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

DEFAULT_PRODUCT_IMAGE = 'productos/imagen_por_defecto.svg'


class CategoriaProducto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    categoria = models.ForeignKey(
        CategoriaProducto,
        on_delete=models.CASCADE
    )

    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()

    imagen_principal = models.ImageField(
        upload_to='productos/',
        default=DEFAULT_PRODUCT_IMAGE,
        null=True,
        blank=True
    )

    imagen_2 = models.ImageField(
        upload_to='productos/',
        null=True,
        blank=True
    )

    imagen_3 = models.ImageField(
        upload_to='productos/',
        null=True,
        blank=True
    )

    imagen_4 = models.ImageField(
        upload_to='productos/',
        null=True,
        blank=True
    )

    precio = models.DecimalField(
            max_digits=10,
            decimal_places=2,
            validators=[
                MinValueValidator(Decimal('0.01')),
                MaxValueValidator(Decimal('99999999.99'))  # Evita guardar precios gigantes en la BD
            ]
        )

    activo = models.BooleanField(default=True)

    disponible_temporada = models.BooleanField(
        default=False,
        verbose_name='Disponible en temporada',
        help_text='Actívalo para mostrar este producto en la sección "Temporada" del sitio.',
    )

    def __str__(self):
        return self.nombre