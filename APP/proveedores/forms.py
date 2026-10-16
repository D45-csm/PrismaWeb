from django import forms

from .models import Proveedor


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['nombre', 'direccion', 'telefono', 'email', 'activo']
        labels = {
            'nombre': 'Nombre',
            'direccion': 'Dirección',
            'telefono': 'Teléfono',
            'email': 'Correo electrónico',
            'activo': 'Activo',
        }
        error_messages = {
            'nombre': {
                'required': 'Escribe el nombre del proveedor.',
                'max_length': 'El nombre no puede superar los 100 caracteres.',
            },
            'email': {
                'invalid': 'Escribe una dirección de correo válida.',
            },
        }
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'autocomplete': 'organization',
            }),
            'direccion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),
            'telefono': forms.TelInput(attrs={
                'class': 'form-control',
                'autocomplete': 'tel',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'autocomplete': 'email',
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }
