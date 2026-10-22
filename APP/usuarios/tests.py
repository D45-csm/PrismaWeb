from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase
from django.conf import settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

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

    def test_cliente_puede_ingresar_con_usuario_correo_o_telefono(self):
        for identificador in (
            self.cliente.username.upper(),
            self.cliente.email.upper(),
            self.cliente.telefono,
        ):
            with self.subTest(identificador=identificador):
                response = self.client.post(
                    reverse('login'),
                    {
                        'username': identificador,
                        'password': 'Clave-segura-2026!',
                    },
                )
                self.assertRedirects(response, reverse('base_cliente'))
                self.client.logout()

    def test_cliente_login_rechaza_caracteres_no_validos_y_telefono_ambiguo(self):
        for identificador in ('cliente\'--', 'cliente con espacios'):
            with self.subTest(identificador=identificador):
                response = self.client.post(
                    reverse('login'),
                    {
                        'username': identificador,
                        'password': 'Clave-segura-2026!',
                    },
                )
                self.assertEqual(response.status_code, 200)
                self.assertFalse(response.context['form'].is_valid())

        Usuario.objects.create_user(
            username='otro-cliente',
            email='otro@example.com',
            telefono=self.cliente.telefono,
            password='Otra-clave-segura-2026!',
        )
        response = self.client.post(
            reverse('login'),
            {
                'username': self.cliente.telefono,
                'password': 'Clave-segura-2026!',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['form'].is_valid())

    def test_mensajes_de_autenticacion_se_muestran_en_su_destino(self):
        self.client.force_login(self.administrador)
        response = self.client.post(reverse('logout'), follow=True)

        self.assertContains(response, 'Has cerrado sesión correctamente.')
        self.assertContains(response, 'id="django-messages"')
        self.assertContains(response, 'js/admin_messages.js')
        self.assertNotContains(response, 'prisma-messages')
        self.assertNotContains(response, 'class="alert alert-success prisma-message"')

        response = self.client.post(
            reverse('admin_login'),
            {
                'username': self.administrador.email,
                'password': 'Clave-segura-2026!',
            },
            follow=True,
        )
        self.assertContains(response, 'Acceso administrativo concedido.')
        self.assertContains(response, 'id="django-messages"')
        self.assertContains(response, 'js/admin_messages.js')

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
        self.assertContains(response_cliente, 'No necesitas Gmail')
        self.assertContains(response_cliente, 'data-password-toggle')
        self.assertContains(response_cliente, 'name="username"')
        self.assertContains(response_cliente, 'name="password"')
        self.assertNotContains(response_cliente, 'Google')
        self.assertNotContains(response_cliente, 'google')
        self.assertNotContains(response_cliente, 'Próximamente')
        self.assertNotContains(response_admin, 'Recordarme en este dispositivo')
        self.assertNotContains(response_admin, '¿Olvidaste tu contraseña?')
        self.assertNotContains(response_admin, 'data-password-toggle')

    def test_login_redirige_a_destino_local_y_rechaza_destino_externo(self):
        response = self.client.post(
            f'{reverse("login")}?next=%2Fproductos%2F',
            {
                'username': self.cliente.email,
                'password': 'Clave-segura-2026!',
                'next': '/productos/',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/productos/')

        self.client.logout()
        response = self.client.post(
            reverse('login'),
            {
                'username': self.cliente.email,
                'password': 'Clave-segura-2026!',
                'next': 'https://example.com/',
            },
        )
        self.assertRedirects(response, reverse('base_cliente'))

    def test_recuperacion_envia_correo_si_el_cliente_existe(self):
        response = self.client.post(
            reverse('recuperar'),
            {'email': self.cliente.email},
            follow=True,
        )

        self.assertContains(response, 'Si el correo está registrado')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.cliente.email, mail.outbox[0].to)

    def test_recuperacion_no_revela_si_el_correo_no_existe(self):
        response = self.client.post(
            reverse('recuperar'),
            {'email': 'nadie@example.com'},
            follow=True,
        )

        self.assertContains(response, 'Si el correo está registrado')
        self.assertEqual(len(mail.outbox), 0)

    def test_recuperacion_no_envia_correo_para_cuentas_administrativas(self):
        response = self.client.post(
            reverse('recuperar'),
            {'email': self.administrador.email},
            follow=True,
        )

        self.assertContains(response, 'Si el correo está registrado')
        self.assertEqual(len(mail.outbox), 0)

    def test_cliente_puede_restablecer_su_contrasena_con_el_enlace(self):
        uid = urlsafe_base64_encode(force_bytes(self.cliente.pk))
        token = default_token_generator.make_token(self.cliente)
        url = reverse('recuperar_confirmar', kwargs={'uidb64': uid, 'token': token})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Crea tu nueva contraseña')

        response = self.client.post(url, {
            'new_password1': 'Otra-clave-mas-segura-2026!',
            'new_password2': 'Otra-clave-mas-segura-2026!',
        })
        self.assertRedirects(response, reverse('login'))

        self.cliente.refresh_from_db()
        self.assertTrue(self.cliente.check_password('Otra-clave-mas-segura-2026!'))

    def test_enlace_de_recuperacion_invalido_no_permite_cambiar_la_contrasena(self):
        uid = urlsafe_base64_encode(force_bytes(self.cliente.pk))
        url = reverse('recuperar_confirmar', kwargs={'uidb64': uid, 'token': 'token-invalido'})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Este enlace ya no es válido')

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

    def test_registro_rechaza_nombre_con_simbolos_y_telefono_no_numerico(self):
        for username, telefono in (
            ('cliente raro!', '3111234567'),
            ('cliente-nuevo', '+57 3111234567'),
        ):
            with self.subTest(username=username, telefono=telefono):
                response = self.client.post(
                    reverse('registro'),
                    {
                        'username': username,
                        'email': f'{username.replace(" ", "-")}@example.com',
                        'telefono': telefono,
                        'password1': 'Fuerte-password-2026!',
                        'password2': 'Fuerte-password-2026!',
                    },
                )
                self.assertEqual(response.status_code, 200)
                self.assertFalse(response.context['form'].is_valid())

    def test_registro_activa_cuenta_cliente_sin_correo_y_no_concede_staff(self):
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

        self.assertRedirects(response, reverse('base_cliente'))
        usuario = Usuario.objects.get(username='nueva')
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
