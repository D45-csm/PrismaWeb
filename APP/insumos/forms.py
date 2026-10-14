from django import forms

from .models import CategoriaInsumo, Insumo


class CategoriaInsumoForm(forms.ModelForm):
    class Meta:
        model = CategoriaInsumo
        fields = ['nombre', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'placeholder': 'Ej. Bebidas frías',
                'class': 'insumo-input',
                'autocomplete': 'off',
            }),
            'descripcion': forms.Textarea(attrs={
                'rows': 3,
                'class': 'insumo-input',
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
        widgets = {
            'nombre': forms.TextInput(attrs={
                'placeholder': 'Ej. Leche entera',
                'class': 'insumo-input',
                'autocomplete': 'off',
            }),
            'descripcion': forms.Textarea(attrs={
                'rows': 3,
                'class': 'insumo-input',
            }),
            'categoria': forms.Select(attrs={'class': 'insumo-input'}),
            'unidad_medida': forms.Select(attrs={'class': 'insumo-input'}),
            'imagen': forms.ClearableFileInput(attrs={
                'accept': 'image/*',
                'class': 'insumo-input',
            }),
        }
