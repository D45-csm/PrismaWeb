from django.test import TestCase

from .forms import RegistroForm


class RegistroFormTests(TestCase):
    def test_registro_form_guarda_telefono(self):
        form = RegistroForm(data={
            'username': 'juanperez',
            'email': 'juan@example.com',
            'telefono': '5512345678',
            'password1': 'TestPassword123!',
            'password2': 'TestPassword123!',
        })

        self.assertTrue(form.is_valid(), form.errors)
        usuario = form.save()
        self.assertEqual(usuario.telefono, '5512345678')
