from uuid import uuid4

from django import forms

from .models import Producto


MAX_PRODUCT_IMAGE_SIZE = 5 * 1024 * 1024
SAFE_IMAGE_EXTENSIONS = {
    'JPEG': '.jpg',
    'PNG': '.png',
    'GIF': '.gif',
    'WEBP': '.webp',
}


class ProductoForm(forms.ModelForm):
    eliminar_imagen_principal = forms.BooleanField(required=False)
    eliminar_imagen_2 = forms.BooleanField(required=False)
    eliminar_imagen_3 = forms.BooleanField(required=False)
    eliminar_imagen_4 = forms.BooleanField(required=False)

    class Meta:
        model = Producto
        fields = [
            'nombre',
            'descripcion',
            'precio',
            'categoria',
            'imagen_principal',
            'imagen_2',
            'imagen_3',
            'imagen_4',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'placeholder': 'Escribe el nombre del producto',
                'autocomplete': 'off',
            }),
            'descripcion': forms.Textarea(attrs={
                'placeholder': 'Escribe una descripción del producto',
            }),
            'precio': forms.NumberInput(attrs={
                'placeholder': '0',
                'step': '0.01',
                'min': '0.01',
            }),
            'categoria': forms.Select(attrs={'id': 'categoria'}),
            'imagen_principal': forms.ClearableFileInput(attrs={
                'accept': 'image/*',
            }),
            'imagen_2': forms.ClearableFileInput(attrs={
                'accept': 'image/*',
            }),
            'imagen_3': forms.ClearableFileInput(attrs={
                'accept': 'image/*',
            }),
            'imagen_4': forms.ClearableFileInput(attrs={
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
