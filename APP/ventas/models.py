from django.db import models
from APP.reserva.models import Reserva 
from APP.productos.models import Producto

class Comprobante(models.Model):
    CHOICES_ESTADO = [
        ('Sin comprobante aun', 'Sin Comprobante Aún'),
        ('Pendiente de confirmación', 'Pendiente de Confirmación'),
        ('Confirmado', 'Confirmado'),
        ('Rechazado', 'Rechazado'),
    ]
    direccion_comprobante = models.FileField(upload_to='comprobantes/')
    estado = models.CharField(max_length=50, choices=CHOICES_ESTADO, default='Pendiente de Confirmación')

    def __str__(self):
        return f"Comprobante #{self.id} - {self.estado}"


class Venta(models.Model):
    # auto_now_add=True registra la fecha automáticamente al crear la venta
    fecha = models.DateField(auto_now_add=True) 
    
    #SET_NULL por si se elimina la reserva, la venta siga existiendo en el historial.
    reserva = models.ForeignKey(Reserva, on_delete=models.SET_NULL, null=True, blank=True)
    
    # RELACIÓN MUCHOS A MUCHOS
    comprobantes = models.ManyToManyField(Comprobante, related_name='ventas', blank=True)

    def __str__(self):
        return f"Venta #{self.id} - Fecha: {self.fecha}"


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    costo_unitario_producto = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.cantidad}x {self.producto.nombre} (Venta #{self.venta.id})"
    
    @property
    def subtotal(self):
        return self.cantidad * self.costo_unitario_producto