import re

from django import forms
from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.models import Group
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.contrib.auth.forms import (
    AuthenticationForm,
    UserCreationForm,
)
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator

from .models import Usuario


class RolForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name', 'permissions']
        labels = {
            'name': 'Nombre del rol',
            'permissions': 'Permisos del rol',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'admin-form-input',
                'placeholder': 'Ej. Administrador de inventario',
                'maxlength': 150,
            }),
            'permissions': forms.CheckboxSelectMultiple,
        }


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Nombre de usuario, correo o teléfono',
        max_length=254,
        widget=forms.TextInput(attrs={
            'autocomplete': 'username',
            'placeholder': 'Tu usuario, correo o teléfono',
            'autofocus': True,
        }),
    )
    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': 'Los datos de acceso no son correctos.',
        'inactive': 'Esta cuenta no está activa. Verifica tu correo electrónico.',
    }

    def clean(self):
        identifier = self.cleaned_data.get('username', '').strip()
        password = self.cleaned_data.get('password')
        if not identifier or not password:
            return self.cleaned_data

        try:
            if '@' in identifier:
                EmailValidator()(identifier)
                users = Usuario.objects.filter(
                    email__iexact=identifier,
                    is_active=True,
                    is_staff=False,
                    is_superuser=False,
                )
            elif re.fullmatch(r'[0-9]{10}', identifier):
                users = Usuario.objects.filter(
                    telefono=identifier,
                    is_active=True,
                    is_staff=False,
                    is_superuser=False,
                )
            else:
                UnicodeUsernameValidator()(identifier)
                users = Usuario.objects.filter(
                    username__iexact=identifier,
                    is_active=True,
                    is_staff=False,
                    is_superuser=False,
                )
        except ValidationError:
            self.add_error('username', 'Ingresa un usuario, correo o teléfono válido.')
            return self.cleaned_data

        matching_users = list(users.order_by('pk')[:2])
        if len(matching_users) != 1:
            raise self.get_invalid_login_error()

        self.user_cache = authenticate(
            self.request,
            username=matching_users[0].get_username(),
            password=password,
        )
        if self.user_cache is None:
            raise self.get_invalid_login_error()
        self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if user.is_staff or user.is_superuser:
            raise ValidationError(
                'Esta cuenta usa el acceso administrativo.',
                code='staff_account',
            )


class CorreoAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={
            'autocomplete': 'email',
            'placeholder': 'tu@correo.com',
        }),
    )

    def clean(self):
        email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if email and password:
            users = list(
                Usuario.objects.filter(email__iexact=email, is_active=True)[:2]
            )
            if len(users) != 1:
                raise self.get_invalid_login_error()

            self.user_cache = authenticate(
                self.request,
                username=users[0].get_username(),
                password=password,
            )
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data


class AdminLoginForm(CorreoAuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not (user.is_staff or user.is_superuser):
            raise ValidationError(
                'Esta cuenta no tiene permisos administrativos.',
                code='not_staff',
            )


class RecuperarPasswordForm(forms.Form):
    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={
            'autocomplete': 'email',
            'placeholder': 'tu@correo.com',
            'autofocus': True,
        }),
    )


class NuevaContrasenaForm(forms.Form):
    """Formulario para definir una nueva contraseña desde el enlace de recuperación."""
    new_password1 = forms.CharField(
        label='Nueva contraseña',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'new-password',
            'placeholder': 'Escribe tu nueva contraseña',
            'autofocus': True,
        }),
    )
    new_password2 = forms.CharField(
        label='Confirma la nueva contraseña',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'new-password',
            'placeholder': 'Repite tu nueva contraseña',
        }),
    )

    def __init__(self, usuario, *args, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)

    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError('Las dos contraseñas no coinciden.', code='password_mismatch')
        if password1:
            password_validation.validate_password(password1, self.usuario)
        return password2

    def save(self, commit=True):
        self.usuario.set_password(self.cleaned_data['new_password1'])
        if commit:
            self.usuario.save()
        return self.usuario


class RegistroForm(UserCreationForm):
    email = forms.EmailField(required=True, label='Correo electrónico')
    telefono = forms.CharField(
        required=True,
        max_length=10,
        label='Teléfono',
        widget=forms.TextInput(attrs={
            'autocomplete': 'tel',
            'inputmode': 'numeric',
            'pattern': '[0-9]{10}',
            'placeholder': '3001234567',
        }),
    )

    class Meta:
        model = Usuario
        fields = ['username', 'email', 'telefono', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.is_active = True
        if commit:
            user.save()
            self.save_m2m()
        return user

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise ValidationError('Ya existe una cuenta con este correo.')
        return email

    def clean_telefono(self):
        telefono = self.cleaned_data['telefono'].strip()
        if not re.fullmatch(r'[0-9]{10}', telefono):
            raise ValidationError('Ingresa un teléfono de 10 dígitos, sin espacios ni símbolos.')
        if Usuario.objects.filter(
            telefono=telefono,
            is_staff=False,
            is_superuser=False,
        ).exists():
            raise ValidationError('Ya existe una cuenta con este teléfono.')
        return telefono
