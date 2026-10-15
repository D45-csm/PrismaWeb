from django.core import mail
from django.test import TestCase, override_settings
from django.conf import settings
from django.urls import reverse

from APP.insumos.models import CategoriaInsumo, Insumo

from .models import Usuario


class AccesoUsuarioTests(TestCase):
    def setUp(self):
        self.cliente = Usuario.objects.create_user(
            username='cliente',
            email='cliente@example.com',
            telefono='3001234567',
            password='Clave-segura-2026!',
        )
        self.administrador = Usuario.objects.create_user(
            username='admin',
            email='admin@example.com',
            telefono='3007654321',
            password='Clave-segura-2026!',
            is_staff=True,
        )

    def test_cliente_ingresa_con_correo_y_contrasena(self):
        response = self.client.post(
            reverse('login'),
            {'username': self.cliente.email, 'password': 'Clave-segura-2026!'},
        )

        self.assertRedirects(response, reverse('base_cliente'))

    def test_mensajes_de_autenticacion_se_muestran_en_su_destino(self):
        self.client.force_login(self.administrador)
        response = self.client.post(reverse('logout'), follow=True)

        self.assertContains(response, 'Has cerrado sesión correctamente.')

        response = self.client.post(
            reverse('admin_login'),
            {
                'username': self.administrador.email,
                'password': 'Clave-segura-2026!',
            },
            follow=True,
        )
        self.assertContains(response, 'Acceso administrativo concedido.')

        response = self.client.get(reverse('gestion_insumos'))
        self.assertNotContains(response, 'Has cerrado sesión correctamente.')
        self.assertNotContains(response, 'Acceso administrativo concedido.')

    def test_portada_se_renderiza_a_traves_de_django(self):
        response = self.client.get(reverse('base_cliente'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nuestros Cheesecakes')
        self.assertNotContains(response, '{%')

    def test_recordarme_extiende_la_sesion_y_sin_marcar_usa_sesion_del_navegador(self):
        response = self.client.post(
            reverse('login'),
            {
                'username': self.cliente.email,
                'password': 'Clave-segura-2026!',
                'remember_me': 'on',
            },
        )
        self.assertRedirects(response, reverse('base_cliente'))
        self.assertEqual(
            self.client.session.get_expiry_age(),
            settings.SESSION_COOKIE_AGE,
        )

        self.client.logout()
        response = self.client.post(
            reverse('login'),
            {
                'username': self.cliente.email,
                'password': 'Clave-segura-2026!',
            },
        )
        self.assertRedirects(response, reverse('base_cliente'))
        self.assertTrue(self.client.session.get_expire_at_browser_close())

    def test_login_muestra_recordarme_y_recuperacion_solo_para_cliente(self):
        response_cliente = self.client.get(reverse('login'))
        response_admin = self.client.get(reverse('admin_login'))

        self.assertContains(response_cliente, 'Recordarme en este dispositivo')
        self.assertContains(response_cliente, '¿Olvidaste tu contraseña?')
        self.assertContains(response_cliente, 'name="username"')
        self.assertContains(response_cliente, 'name="password"')
        self.assertNotContains(response_cliente, 'Google')
        self.assertNotContains(response_cliente, 'google')
        self.assertNotContains(response_cliente, 'Próximamente')
        self.assertNotContains(response_admin, 'Recordarme en este dispositivo')
        self.assertNotContains(response_admin, '¿Olvidaste tu contraseña?')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_recuperar_contrasena_envia_enlace_y_permite_cambiarla(self):
        response = self.client.post(
            reverse('recuperar'),
            {'email': self.cliente.email},
        )

        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.cliente.email])

        reset_url = next(
            line.strip()
            for line in mail.outbox[0].body.splitlines()
            if '/usuarios/recuperar/confirmar/' in line
        )
        reset_path = '/usuarios/' + reset_url.split('/usuarios/', 1)[1]
        reset_response = self.client.get(reset_path, follow=True)
        self.assertEqual(reset_response.status_code, 200)
        if reset_response.redirect_chain:
            reset_path = reset_response.redirect_chain[-1][0]
        response = self.client.post(
            reset_path,
            {
                'new_password1': 'Otra-clave-fuerte-2026!',
                'new_password2': 'Otra-clave-fuerte-2026!',
            },
        )
        self.assertRedirects(response, reverse('password_reset_complete'))

        self.cliente.refresh_from_db()
        self.assertTrue(self.cliente.check_password('Otra-clave-fuerte-2026!'))

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend')
    def test_recuperar_avisa_si_el_correo_esta_en_modo_consola(self):
        response = self.client.get(reverse('recuperar'))

        self.assertContains(response, 'en la consola del servidor')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_recuperacion_no_envia_enlace_a_cuentas_administrativas(self):
        response = self.client.post(
            reverse('recuperar'),
            {'email': self.administrador.email},
        )

        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(mail.outbox, [])

    def test_rechaza_contrasena_incorrecta_y_accesos_cruzados(self):
        for url_name, email in (
            ('login', self.administrador.email),
            ('admin_login', self.cliente.email),
        ):
            with self.subTest(url=url_name):
                response = self.client.post(
                    reverse(url_name),
                    {'username': email, 'password': 'incorrecta'},
                )
                self.assertEqual(response.status_code, 200)
                self.assertFalse(response.context['form'].is_valid())

    def test_cuentas_solo_entran_en_su_tipo_de_acceso(self):
        response_cliente = self.client.post(
            reverse('admin_login'),
            {'username': self.cliente.email, 'password': 'Clave-segura-2026!'},
        )
        self.assertFalse(response_cliente.context['form'].is_valid())

        response_admin = self.client.post(
            reverse('login'),
            {'username': self.administrador.email, 'password': 'Clave-segura-2026!'},
        )
        self.assertFalse(response_admin.context['form'].is_valid())

    def test_cliente_sin_staff_no_puede_abrir_panel_ni_categorias(self):
        self.client.force_login(self.cliente)

        for url_name in ('perfil', 'gestion_categorias_insumos'):
            with self.subTest(url=url_name):
                response = self.client.get(reverse(url_name))
                self.assertRedirects(
                    response,
                    f'{reverse("admin_login")}?next={reverse(url_name)}',
                )

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_registro_exige_confirmar_correo_y_no_concede_staff(self):
        response = self.client.post(
            reverse('registro'),
            {
                'username': 'nueva',
                'email': 'nueva@example.com',
                'telefono': '3111234567',
                'password1': 'Fuerte-password-2026!',
                'password2': 'Fuerte-password-2026!',
            },
        )

        self.assertRedirects(response, reverse('registro'))
        usuario = Usuario.objects.get(username='nueva')
        self.assertFalse(usuario.is_active)
        self.assertFalse(usuario.is_staff)
        self.assertEqual(len(mail.outbox), 1)

        verification_path = mail.outbox[0].body.splitlines()[3]
        invalid_verification_path = verification_path.rsplit('/', 2)[0] + '/invalid/'
        self.client.get(invalid_verification_path)
        usuario.refresh_from_db()
        self.assertFalse(usuario.is_active)

        verification_response = self.client.get(verification_path)
        self.assertRedirects(verification_response, reverse('base_cliente'))

        usuario.refresh_from_db()
        self.assertTrue(usuario.is_active)
        self.assertFalse(usuario.is_staff)
        self.assertEqual(
            self.client.session['_auth_user_id'],
            str(usuario.pk),
        )


class GestionCategoriasInsumosTests(TestCase):
    def setUp(self):
        self.administrador = Usuario.objects.create_user(
            username='admin',
            email='admin@example.com',
            telefono='3007654321',
            password='Clave-segura-2026!',
            is_staff=True,
        )
        self.client.force_login(self.administrador)

    def test_admin_ve_panel_y_gestion_de_categorias(self):
        self.assertEqual(self.client.get(reverse('perfil')).status_code, 200)
        self.assertEqual(
            self.client.get(reverse('gestion_categorias_insumos')).status_code,
            200,
        )

    def test_admin_inicia_sesion_en_acceso_privado(self):
        self.client.logout()
        response = self.client.post(
            reverse('admin_login'),
            {
                'username': self.administrador.email,
                'password': 'Clave-segura-2026!',
            },
        )
        self.assertRedirects(response, reverse('perfil'))

    def test_admin_crea_categoria_y_busca_insumos_sin_filtrar_por_categoria(self):
        response = self.client.post(
            reverse('gestion_categorias_insumos'),
            {
                'accion': 'crear_categoria',
                'nombre': 'Bebidas frías',
                'descripcion': 'Bebidas y preparaciones frías',
            },
        )
        categoria = CategoriaInsumo.objects.get(nombre='Bebidas frías')
        self.assertRedirects(response, reverse('gestion_categorias_insumos'))

        response = self.client.post(
            f'{reverse("gestion_categorias_insumos")}?categoria={categoria.pk}',
            {
                'accion': 'crear_insumo',
                'nombre': 'Leche',
                'descripcion': 'Leche para bebidas',
                'categoria': categoria.pk,
                'unidad_medida': 'ml',
            },
        )
        self.assertRedirects(
            response,
            f'{reverse("gestion_categorias_insumos")}?q=Leche&campo=nombre',
        )

        otra_categoria = CategoriaInsumo.objects.create(nombre='Limpieza')
        Insumo.objects.create(
            nombre='Detergente',
            categoria=otra_categoria,
            unidad_medida='u',
        )

        response = self.client.get(
            reverse('gestion_categorias_insumos'),
            {'q': 'Leche', 'campo': 'nombre'},
        )
        self.assertEqual(
            list(response.context['insumos'].values_list('nombre', flat=True)),
            ['Leche'],
        )

        response = self.client.get(
            reverse('gestion_categorias_insumos'),
            {'categoria': categoria.pk, 'q': 'Detergente', 'campo': 'nombre'},
        )
        self.assertEqual(
            list(response.context['insumos'].values_list('nombre', flat=True)),
            ['Detergente'],
        )
