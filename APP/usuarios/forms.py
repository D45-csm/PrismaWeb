import re
import unicodedata

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


class UsuarioAdminForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['username', 'email', 'telefono', 'is_active']
        labels = {
            'username': 'Nombre de usuario',
            'email': 'Correo electrónico',
            'telefono': 'Teléfono',
            'is_active': 'Está activo',
        }
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'insumo-input',
                'autocomplete': 'username',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'insumo-input',
                'autocomplete': 'email',
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'insumo-input',
                'autocomplete': 'tel',
                'inputmode': 'numeric',
                'pattern': '[0-9]{10}',
                'maxlength': '10',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'insumo-checkbox',
            }),
        }

    def __init__(self, *args, include_role=False, **kwargs):
        if not args and not kwargs.get('data') and not kwargs.get('instance'):
            kwargs['initial'] = {
                **kwargs.get('initial', {}),
                'is_active': True,
            }
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True
        if include_role:
            rol_actual = None
            if self.instance.pk and self.instance.groups.count() == 1:
                rol_actual = self.instance.groups.first()
            self.fields['rol'] = forms.ModelChoiceField(
                queryset=Group.objects.order_by('name'),
                required=False,
                label='Rol',
                initial=rol_actual,
                empty_label='Sin rol',
                widget=forms.Select(attrs={'class': 'insumo-input'}),
            )

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        duplicados = Usuario.objects.filter(email__iexact=email)
        if self.instance.pk:
            duplicados = duplicados.exclude(pk=self.instance.pk)
        if duplicados.exists():
            raise ValidationError('Ya existe una cuenta con este correo.')
        return email

    def clean_telefono(self):
        telefono = self.cleaned_data['telefono'].strip()
        if not re.fullmatch(r'[0-9]{10}', telefono):
            raise ValidationError(
                'Ingresa un teléfono de 10 dígitos, sin espacios ni símbolos.'
            )
        if not (self.instance.is_staff or self.instance.is_superuser):
            duplicados = Usuario.objects.filter(
                telefono=telefono,
                is_staff=False,
                is_superuser=False,
            )
            if self.instance.pk:
                duplicados = duplicados.exclude(pk=self.instance.pk)
            if duplicados.exists():
                raise ValidationError('Ya existe una cuenta con este teléfono.')
        return telefono

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if not usuario.pk:
            usuario.set_unusable_password()
        if commit:
            usuario.save()
            self.save_m2m()
        return usuario


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Correo electrónico o teléfono',
        max_length=254,
        widget=forms.TextInput(attrs={
            'autocomplete': 'username',
            'placeholder': 'Tu correo o teléfono',
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


class CodigoRecuperacionForm(forms.Form):
    code = forms.RegexField(
        regex=r'^[0-9]{8}$',
        label='Código de recuperación',
        error_messages={'invalid': 'Ingresa el código de 8 dígitos que recibiste por correo.'},
        widget=forms.TextInput(attrs={
            'autocomplete': 'one-time-code',
            'inputmode': 'numeric',
            'pattern': '[0-9]{8}',
            'maxlength': '8',
            'placeholder': '12345678',
            'autofocus': True,
        }),
    )


class NuevaContrasenaForm(forms.Form):
    """Formulario para definir una contraseña tras verificar el código de recuperación."""
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
    first_name = forms.CharField(
        required=True,
        max_length=80,
        label='Nombre',
        widget=forms.TextInput(attrs={
            'autocomplete': 'given-name',
            'placeholder': 'Tu nombre',
            'maxlength': 80,
        }),
    )
    last_name = forms.CharField(
        required=True,
        max_length=80,
        label='Apellido',
        widget=forms.TextInput(attrs={
            'autocomplete': 'family-name',
            'placeholder': 'Tu apellido',
            'maxlength': 80,
        }),
    )
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
        fields = ['first_name', 'last_name', 'email', 'telefono', 'password1', 'password2']

    def clean_first_name(self):
        return self._clean_person_name('first_name')

    def clean_last_name(self):
        return self._clean_person_name('last_name')

    def _clean_person_name(self, field_name):
        value = ' '.join(self.cleaned_data[field_name].split())
        if (
            len(value) < 2
            or not re.fullmatch(r"[^\W\d_]+(?:[ '-][^\W\d_]+)*", value, re.UNICODE)
        ):
            raise ValidationError(
                'Usa solo letras; puedes incluir espacios, guiones o apóstrofos.',
            )
        return value

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self._available_username()
        user.email = self.cleaned_data['email']
        user.is_active = True
        if commit:
            user.save()
            self.save_m2m()
        return user

    def _available_username(self):
        def normalize(value):
            normalized = unicodedata.normalize('NFKD', value)
            return ''.join(
                character for character in normalized
                if character.isascii() and character.isalnum()
            ).lower()

        base = '.'.join(filter(None, (
            normalize(self.cleaned_data['first_name']),
            normalize(self.cleaned_data['last_name']),
        ))) or 'cliente'
        username = base[:150]
        suffix = 1
        while Usuario.objects.filter(username__iexact=username).exists():
            suffix_text = str(suffix)
            username = f'{base[:150 - len(suffix_text) - 1]}{suffix_text}'
            suffix += 1
        return username

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
