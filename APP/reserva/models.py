from django.db import models
from APP.usuarios.models import Usuario
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
    fecha_realizacion = models.DateTimeField(auto_now_add=True)
    fecha_reserva = models.DateField()
    hora = models.TimeField()
    numero_personas = models.PositiveIntegerField(null=True, blank=True, )
    tipo_reserva = models.CharField(max_length=50, choices=choices_tipo_reserva, default='Para llevar')
    detalles = models.TextField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=choices_estado, default='Pendiente')
    asistencia = models.CharField(max_length=20, choices=choice_asistencia, blank=True , null=True)

    def __str__(self):
        nombre = self.usuario.username if self.usuario else "Usuario Eliminado/Invitado"
        return f"Reserva de {nombre} el {self.fecha_reserva} a las {self.hora}"