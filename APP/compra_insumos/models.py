from django.db import models
from usuarios.models import Usuario
from proveedores.models import Proveedor
from insumos.models import Insumo

class CompraInsumo(models.Model):
    # La fecha se puede autogenerar o dejar manual. auto_now_add=True la pone automáticamente al crear el registro.
    fecha = models.DateField(auto_now_add=True) 
    
    # Relación con Proveedor (app proveedores)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT) 
    # Relación con Usuario
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Compra #{self.id} - {self.proveedor.nombre_empresa} ({self.fecha})"

class DetalleCompraInsumo(models.Model):
    unidad_medida_choices = [
        ('g', 'Gramo'),
        ('ml', 'Mililitro'),
        ('kg', 'Kilogramo'),
        ('l', 'Litro'),
        ('u', 'Unidad'),
    ]
    # related_name='detalles' te permitirá buscar los detalles desde la compra fácilmente (ej: mi_compra.detalles.all())
    compra = models.ForeignKey(CompraInsumo, on_delete=models.CASCADE, related_name='detalles')
    
    # Relación con Insumo (app insumos)
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    unidad_medida = models.CharField(max_length=20, choices=unidad_medida_choices)
    costo = models.DecimalField(max_digits=10, decimal_places=2) 

    def __str__(self):
        return f"{self.cantidad} {self.get_unidad_medida_display()} de {self.insumo.nombre} (Compra #{self.compra.id})"

    @property
    def subtotal(self):
        return self.cantidad * self.costo