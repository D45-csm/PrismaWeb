from django import forms

from .models import CategoriaInsumo, Insumo


class CategoriaInsumoForm(forms.ModelForm):
    class Meta:
        model = CategoriaInsumo
        fields = ['nombre', 'descripcion']
        labels = {
            'nombre': 'Nombre de la categoría',
            'descripcion': 'Descripción',
        }
        error_messages = {
            'nombre': {
                'required': 'Escribe el nombre de la categoría.',
                'max_length': 'El nombre no puede superar los 100 caracteres.',
            },
        }
        widgets = {
            'nombre': forms.TextInput(attrs={
                'placeholder': 'Ej. Bebidas frías',
                'class': 'form-control insumo-input',
                'autocomplete': 'off',
            }),
            'descripcion': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control insumo-input',
            }),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        duplicado = CategoriaInsumo.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            duplicado = duplicado.exclude(pk=self.instance.pk)
        if duplicado.exists():
            raise forms.ValidationError('Ya existe una categoría con ese nombre.')
        return nombre


class InsumoForm(forms.ModelForm):
    class Meta:
        model = Insumo
        fields = ['nombre', 'descripcion', 'categoria', 'unidad_medida', 'imagen']
        labels = {
            'nombre': 'Nombre del insumo',
            'descripcion': 'Descripción',
            'categoria': 'Categoría',
            'unidad_medida': 'Unidad de medida',
            'imagen': 'Imagen',
        }
        error_messages = {
            'nombre': {
                'required': 'Escribe el nombre del insumo.',
                'max_length': 'El nombre no puede superar los 100 caracteres.',
            },
            'categoria': {
                'required': 'Selecciona una categoría.',
            },
            'unidad_medida': {
                'required': 'Selecciona una unidad de medida.',
            },
        }
        widgets = {
            'nombre': forms.TextInput(attrs={
                'placeholder': 'Ej. Leche entera',
                'class': 'form-control insumo-input',
                'autocomplete': 'off',
            }),
            'descripcion': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control insumo-input',
            }),
            'categoria': forms.Select(attrs={
                'class': 'form-select insumo-input js-select2',
            }),
            'unidad_medida': forms.Select(attrs={
                'class': 'form-select insumo-input',
            }),
            'imagen': forms.ClearableFileInput(attrs={
                'accept': 'image/*',
                'class': 'form-control insumo-input',
            }),
        }
