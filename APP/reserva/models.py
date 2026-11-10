from django.db import models
from APP.usuarios.models import Usuario
from APP.productos.models import Producto


# Create your models here.
class Reserva(models.Model):
    choices_estado = [
        ('Pendiente', 'Pendiente'),
        ('Confirmada', 'Confirmada'),
        ('Cancelada', 'Cancelada'),
    ]

    choice_asistencia = [
        ('Asistió', 'Asistió'),
        ('No asistió', 'No asistió'),
    ]

    choices_tipo_reserva = [
        ('Mesa', 'Mesa'),
        ('Para llevar', 'Para llevar'),
    ]
    usuario = models.ForeignKey( Usuario , on_delete=models.SET_NULL, null=True, blank=True)
    nombre_cliente = models.CharField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=30, blank=True)
    fecha_realizacion = models.DateTimeField(auto_now_add=True)
    fecha_reserva = models.DateField()
    hora = models.TimeField(blank=True, null=True)
    numero_personas = models.PositiveIntegerField(null=True, blank=True, )
    tipo_reserva = models.CharField(max_length=50, choices=choices_tipo_reserva, default='Para llevar')
    detalles = models.TextField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=choices_estado, default='Pendiente')
    asistencia = models.CharField(max_length=20, choices=choice_asistencia, blank=True , null=True)

    def __str__(self):
        nombre = self.usuario.username if self.usuario else "Usuario Eliminado/Invitado"
        return f"Reserva de {nombre} el {self.fecha_reserva} a las {self.hora}"


class DetalleReserva(models.Model):
    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        related_name='lineas',
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='detalles_reserva',
    )
    nombre_producto = models.CharField(max_length=120)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.cantidad}x {self.nombre_producto} (Reserva #{self.reserva_id})"

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario