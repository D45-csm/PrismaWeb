from django.db import models
from APP.usuarios.models import Usuario
from APP.insumos.models import Insumo

class Movimiento(models.Model):
    # Opciones para estandarizar las entradas y salidas
    tipo_accion = [
        ('ENTRADA', 'Entrada'),
        ('SALIDA', 'Salida'),
    ]
    
    origenes= [
        ('COMPRA', 'Compra a proveedor'),
        ('RECETA', 'Consumo por receta'),
        ('AJUSTE', 'Ajuste manual'),
    ]

    unidad_medida_choices = [
        ('g', 'Gramo'),
        ('ml', 'Mililitro'),
        ('kg', 'Kilogramo'),
        ('l', 'Litro'),
        ('cajas', 'Cajas'),
        ('u', 'Unidad'),
    ]

    # campos con choices para estandarizar los tipos de movimiento y su origen
    origen = models.CharField(max_length=20, choices=origenes)
    accion = models.CharField(max_length=20, choices=tipo_accion)
    fecha_movimiento = models.DateTimeField(auto_now_add=True)
    
    # set_null para mantener el historial si se borra un usuario y PROTECT para evitar borrar un insumo que tiene movimientos asociados
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT)
    
    #DecimalField para unidades decimales, max_digits es el total de dígitos y decimal_places es la cantidad de dígitos después del punto decimal
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    unidad_medida = models.CharField(max_length=20, choices=unidad_medida_choices)

    def __str__(self):
        return f"{self.accion} - {self.insumo.nombre} ({self.cantidad} {self.unidad_medida})"