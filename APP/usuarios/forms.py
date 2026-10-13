from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Usuario


class RegistroForm(UserCreationForm):
    telefono = forms.CharField(
        max_length=10,
        required=True,
        label='Teléfono',
        help_text='Ingrese un número de 10 dígitos.'
    )

    class Meta:
        model = Usuario
        fields = ['username', 'email', 'telefono', 'password1', 'password2']

    def clean_telefono(self):
        telefono = self.cleaned_data['telefono']
        if not telefono.isdigit() or len(telefono) != 10:
            raise forms.ValidationError('El teléfono debe tener exactamente 10 dígitos.')
        return telefono

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.telefono = self.cleaned_data['telefono']
        if commit:
            usuario.save()
        return usuario


class LoginForm(AuthenticationForm):
    pass