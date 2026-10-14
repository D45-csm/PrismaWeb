from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    UserCreationForm,
)
from django.core.exceptions import ValidationError

from .models import Usuario


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


class LoginForm(CorreoAuthenticationForm):
    error_messages = {
        **CorreoAuthenticationForm.error_messages,
        'invalid_login': 'El correo electrónico o la contraseña no son correctos.',
        'inactive': 'Esta cuenta no está activa. Verifica tu correo electrónico.',
    }

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if user.is_staff or user.is_superuser:
            raise ValidationError(
                'Esta cuenta usa el acceso administrativo.',
                code='staff_account',
            )


class ClientePasswordResetForm(PasswordResetForm):
    def get_users(self, email):
        return (
            user
            for user in super().get_users(email)
            if not user.is_staff and not user.is_superuser
        )


class AdminLoginForm(CorreoAuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not (user.is_staff or user.is_superuser):
            raise ValidationError(
                'Esta cuenta no tiene permisos administrativos.',
                code='not_staff',
            )


class RegistroForm(UserCreationForm):
    email = forms.EmailField(required=True, label='Correo electrónico')
    telefono = forms.CharField(
        required=True,
        max_length=10,
        label='Teléfono',
        widget=forms.TextInput(attrs={'autocomplete': 'tel'}),
    )

    class Meta:
        model = Usuario
        fields = ['username', 'email', 'telefono', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.is_active = False
        if commit:
            user.save()
            self.save_m2m()
        return user

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise ValidationError('Ya existe una cuenta con este correo.')
        return email
