from django import forms

from .models import Proveedor


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['nombre', 'direccion', 'telefono', 'email']
        labels = {
            'nombre': 'Nombre del proveedor',
            'direccion': 'Dirección',
            'telefono': 'Teléfono',
            'email': 'Correo electrónico',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'insumo-input',
                'autocomplete': 'organization',
                'maxlength': 100,
            }),
            'direccion': forms.Textarea(attrs={
                'class': 'insumo-input',
                'rows': 3,
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'insumo-input',
                'autocomplete': 'tel',
                'maxlength': 20,
            }),
            'email': forms.EmailInput(attrs={
                'class': 'insumo-input',
                'autocomplete': 'email',
            }),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        duplicados = Proveedor.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            duplicados = duplicados.exclude(pk=self.instance.pk)
        if duplicados.exists():
            raise forms.ValidationError('Ya existe un proveedor con ese nombre.')
        return nombre
