from django import forms
from .models import Proveedor

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['nombre', 'direccion', 'telefono', 'email', 'activo']
        
        # Personalizar las etiquetas que verá el usuario
        labels = {
            'nombre': 'Nombre o Razón Social',
            'direccion': 'Dirección Completa',
            'telefono': 'Teléfono de Contacto',
            'email': 'Correo Electrónico',
            'activo': 'Proveedor Activo',
        }
        
        # Asignar clases CSS y atributos a los inputs (widgets)
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ej. Insumos PRISMA S.A.S.'
            }),
            'direccion': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'Ej. Calle Falsa 123, Local 4',
                'rows': 3
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ej. 300 123 4567',
                'type': 'tel'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'contacto@proveedor.com',
                'type': 'email'
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
        }