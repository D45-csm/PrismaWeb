from uuid import uuid4

from django import forms

from .models import CategoriaProducto, Producto


MAX_PRODUCT_IMAGE_SIZE = 5 * 1024 * 1024
SAFE_IMAGE_EXTENSIONS = {
    'JPEG': '.jpg',
    'PNG': '.png',
    'GIF': '.gif',
    'WEBP': '.webp',
}


class CategoriaProductoForm(forms.ModelForm):
    class Meta:
        model = CategoriaProducto
        fields = ['nombre', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'placeholder': 'Ej. Postres',
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
        if not nombre:
            raise forms.ValidationError('Ingresa el nombre de la categoría.')
        duplicado = CategoriaProducto.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            duplicado = duplicado.exclude(pk=self.instance.pk)
        if duplicado.exists():
            raise forms.ValidationError('Ya existe una categoría con ese nombre.')
        return nombre


class ProductoForm(forms.ModelForm):
    eliminar_imagen_principal = forms.BooleanField(required=False)
    eliminar_imagen_2 = forms.BooleanField(required=False)
    eliminar_imagen_3 = forms.BooleanField(required=False)
    eliminar_imagen_4 = forms.BooleanField(required=False)
    disponible_temporada = forms.BooleanField(
        required=False,
        label='Mostrar en Temporada',
        help_text='Aparecerá en la sección "Temporada" del sitio para clientes.',
    )

    class Meta:
        model = Producto
        fields = [
            'nombre',
            'descripcion',
            'precio',
            'categoria',
            'activo',
            'disponible_temporada',
            'imagen_principal',
            'imagen_2',
            'imagen_3',
            'imagen_4',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'insumo-input',
                'placeholder': 'Escribe el nombre del producto',
                'autocomplete': 'off',
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'insumo-input',
                'placeholder': 'Escribe una descripción del producto',
            }),
            'precio': forms.NumberInput(attrs={
                'class': 'insumo-input',
                'placeholder': '0',
                'step': '0.01',
                'min': '0.01',
            }),
            'categoria': forms.Select(attrs={'id': 'categoria', 'class': 'insumo-input'}),
            'imagen_principal': forms.FileInput(attrs={
                'class': 'insumo-input',
                'accept': 'image/*',
            }),
            'imagen_2': forms.FileInput(attrs={
                'class': 'insumo-input',
                'accept': 'image/*',
            }),
            'imagen_3': forms.FileInput(attrs={
                'class': 'insumo-input',
                'accept': 'image/*',
            }),
            'imagen_4': forms.FileInput(attrs={
                'class': 'insumo-input',
                'accept': 'image/*',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].empty_label = 'Selecciona una categoría'

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        if not nombre:
            raise forms.ValidationError('Ingresa el nombre del producto.')
        return nombre

    def clean_descripcion(self):
        descripcion = self.cleaned_data['descripcion'].strip()
        if not descripcion:
            raise forms.ValidationError('Ingresa la descripción del producto.')
        return descripcion

    def clean(self):
        cleaned_data = super().clean()
        for field_name in (
            'imagen_principal',
            'imagen_2',
            'imagen_3',
            'imagen_4',
        ):
            uploaded_image = self.files.get(field_name)
            if not uploaded_image:
                continue
            if uploaded_image.size > MAX_PRODUCT_IMAGE_SIZE:
                self.add_error(
                    field_name,
                    'Cada imagen debe pesar como máximo 5 MB.',
                )
                continue

            image = cleaned_data.get(field_name)
            image_format = getattr(
                getattr(image, 'image', None),
                'format',
                None,
            )
            if image is None:
                continue
            extension = SAFE_IMAGE_EXTENSIONS.get(image_format)
            if not extension:
                self.add_error(
                    field_name,
                    'Usa una imagen JPEG, PNG, GIF o WEBP.',
                )
                continue
            image.name = f'{uuid4().hex}{extension}'
        return cleaned_data
