import re

from django import forms
from django.utils import timezone

from .models import Reserva


POSTRES = {
    'Manzana Verde Cheesecake': 25000,
    'Café Chocolate': 28000,
    'Fresa Chocolate': 32000,
    'Postre Personalizado': 0,
}


class ReservaForm(forms.ModelForm):
    cantidad = forms.IntegerField(
        min_value=1,
        max_value=50,
        label='Cantidad de postres',
        error_messages={
            'required': 'La cantidad debe estar entre 1 y 50 postres.',
            'invalid': 'La cantidad debe estar entre 1 y 50 postres.',
            'min_value': 'La cantidad debe estar entre 1 y 50 postres.',
            'max_value': 'La cantidad debe estar entre 1 y 50 postres.',
        },
        widget=forms.NumberInput(attrs={
            'id': 'cantidad',
            'min': 1,
            'max': 50,
            'value': 1,
        }),
    )
    postre = forms.ChoiceField(
        choices=[
            ('', 'Selecciona un postre'),
            *(
                (
                    nombre,
                    f'{nombre} (a cotizar)' if precio == 0 else nombre,
                )
                for nombre, precio in POSTRES.items()
            ),
        ],
        error_messages={
            'invalid_choice': 'Selecciona uno de los postres disponibles.',
        },
        widget=forms.Select(attrs={'id': 'postre'}),
    )
    detalles = forms.CharField(
        required=False,
        max_length=500,
        label='¿Cómo quieres tu reserva?',
        error_messages={
            'max_length': 'Las indicaciones no pueden superar 500 caracteres.',
        },
        widget=forms.Textarea(attrs={
            'id': 'detalles',
            'rows': 4,
            'maxlength': 500,
            'placeholder': (
                'Cuéntanos la ocasión, mensaje en el postre, sabores, '
                'alergias u hora preferida de entrega…'
            ),
        }),
    )

    class Meta:
        model = Reserva
        fields = [
            'nombre_cliente',
            'telefono',
            'fecha_reserva',
            'postre',
            'cantidad',
            'detalles',
        ]
        labels = {
            'nombre_cliente': 'Nombre completo',
            'telefono': 'Teléfono',
            'fecha_reserva': 'Fecha de entrega',
            'postre': 'Postre deseado',
            'cantidad': 'Cantidad de postres',
            'detalles': '¿Cómo quieres tu reserva?',
        }
        error_messages = {
            'nombre_cliente': {
                'required': 'Ingresa tu nombre (máximo 100 caracteres).',
                'max_length': 'Ingresa tu nombre (máximo 100 caracteres).',
            },
            'telefono': {
                'required': 'Ingresa un número de teléfono válido.',
                'max_length': 'Ingresa un número de teléfono válido.',
            },
            'fecha_reserva': {
                'required': 'Revisa la fecha de entrega.',
                'invalid': 'Revisa la fecha de entrega.',
            },
        }
        widgets = {
            'nombre_cliente': forms.TextInput(attrs={
                'id': 'nombre',
                'maxlength': 100,
                'placeholder': 'Tu nombre',
                'autocomplete': 'name',
            }),
            'telefono': forms.TelInput(attrs={
                'id': 'telefono',
                'maxlength': 30,
                'placeholder': '300 123 4567',
                'autocomplete': 'tel',
            }),
            'fecha_reserva': forms.DateInput(attrs={
                'id': 'fecha',
                'type': 'date',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nombre_cliente'].required = True
        self.fields['telefono'].required = True

    def clean_nombre_cliente(self):
        nombre = (self.cleaned_data.get('nombre_cliente') or '').strip()
        if not nombre:
            raise forms.ValidationError(
                'Ingresa tu nombre (máximo 100 caracteres).',
            )
        return nombre

    def clean_telefono(self):
        telefono = self.cleaned_data['telefono'].strip()
        if not re.fullmatch(r'\+?[\d\s().-]{7,30}', telefono):
            raise forms.ValidationError('Ingresa un número de teléfono válido.')
        return telefono

    def clean_fecha_reserva(self):
        fecha = self.cleaned_data['fecha_reserva']
        if fecha < timezone.localdate():
            raise forms.ValidationError(
                'La fecha de entrega no puede estar en el pasado.',
            )
        return fecha
