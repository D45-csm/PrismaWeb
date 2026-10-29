from datetime import timedelta
from email import policy as email_policy
from html import unescape
import re
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth.hashers import check_password, make_password
from django.core import mail
from django.core.cache import cache
from django.contrib.auth.models import Group, Permission
from django.test import TestCase, override_settings
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from APP.insumos.models import CategoriaInsumo, Insumo
from APP.proveedores.models import Proveedor

from .forms import RegistroForm, RolForm
from .models import Usuario


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AccesoUsuarioTests(TestCase):
    def setUp(self):
        cache.clear()
        self.cliente = Usuario.objects.create_user(
            username='cliente',
            email='cliente@example.com',
            telefono='3001234567',
            password='Clave-segura-2026!',
        )
        self.codigo_recuperacion = '34890127'
        self.cliente.recovery_code_hash = make_password(self.codigo_recuperacion)
        self.cliente.save(update_fields=['recovery_code_hash'])
        self.administrador = Usuario.objects.create_user(
            username='admin',
            email='admin@example.com',
            telefono='3007654321',
            password='Clave-segura-2026!',
            is_staff=True,
        )

    def solicitar_codigo_por_correo(self, email=None):
        response = self.client.post(
            reverse('recuperar'),
            {'email': email or self.cliente.email},
        )
        self.assertRedirects(response, reverse('recuperar_codigo'))
        self.assertEqual(len(mail.outbox), 1)
        codigo = re.search(r'\b[0-9]{8}\b', mail.outbox[0].body)
        self.assertIsNotNone(codigo)
        return codigo.group()

    def test_cliente_ingresa_con_correo_y_contrasena(self):
        response = self.client.post(
            reverse('login'),
            {'username': self.cliente.email, 'password': 'Clave-segura-2026!'},
        )

        self.assertRedirects(response, reverse('base_cliente'))

    def test_login_bloquea_intentos_fallidos_repetidos(self):
        for _ in range(settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS):
            response = self.client.post(
                reverse('login'),
                {
                    'username': self.cliente.email,
                    'password': 'contrasena-incorrecta',
                },
            )
            self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse('login'),
            {
                'username': self.cliente.email,
                'password': 'Clave-segura-2026!',
            },
        )

        self.assertEqual(response.status_code, 429)
        self.assertContains(response, 'Demasiados intentos', status_code=429)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

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
            reverse('login'),
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
        self.assertContains(response, 'mobile-menu-dock')
        self.assertContains(response, 'https://www.tiktok.com/@pasteleriaprisma')
        self.assertContains(response, 'https://www.instagram.com/prisma_pasteleria1/')
        self.assertNotContains(response, '{%')

    def test_contacto_muestra_canales_y_redes_con_el_usuario_de_prisma(self):
        response = self.client.get(reverse('contactos'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Síguenos en redes sociales')
        self.assertContains(
            response,
            'https://mail.google.com/mail/?view=cm&amp;fs=1&amp;to=juansebastiangirataguarin12%40gmail.com&amp;su=Consulta%20para%20Prisma',
        )
        self.assertContains(response, 'tel:+573118689862')
        self.assertContains(response, '@prisma_pasteleria1')
        self.assertContains(response, 'TikTok · @pasteleriaprisma')
        self.assertContains(response, 'fab fa-tiktok')
        self.assertContains(response, 'fab fa-instagram')
        self.assertContains(response, 'https://maps.app.goo.gl/MkcuMJTPRKyRcEWt6?g_st=ic')
        self.assertContains(
            response,
            'https://mail.google.com/mail/?view=cm&amp;fs=1&amp;to=juansebastiangirataguarin12%40gmail.com&amp;su=Consulta%20para%20Prisma',
        )
        self.assertNotContains(response, 'whatsapp-float')

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

    def test_login_unificado_muestra_seguridad_y_recuperacion_por_rol(self):
        response = self.client.get(reverse('login'))

        self.assertContains(response, 'Recordarme en este dispositivo')
        self.assertContains(response, 'Correo, teléfono o nombre de usuario')
        self.assertContains(response, 'data-password-toggle')
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')
        self.assertContains(response, 'logo_prisma.png')
        self.assertContains(response, reverse('recuperar'))
        self.assertContains(response, reverse('admin_recuperar'))
        self.assertNotContains(response, 'Acceso para administración')
        self.assertNotContains(response, 'Google')
        self.assertNotContains(response, 'google')
        self.assertNotContains(response, 'Próximamente')

        response_admin_alias = self.client.get(reverse('admin_login'))
        self.assertRedirects(response_admin_alias, reverse('login'))

        response_home = self.client.get(reverse('base_cliente'))
        self.assertNotContains(response_home, 'Código de recuperación')

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

    def test_enlace_codigo_en_login_lleva_al_codigo_tras_autenticar_cliente(self):
        url_codigo = reverse('codigo_recuperacion_cuenta')
        response = self.client.get(url_codigo)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])
        self.assertIn('next=', response['Location'])

        response = self.client.get(response['Location'])
        self.assertContains(response, f'value="{url_codigo}"')
        self.assertContains(response, 'te llevaremos a generar o renovar tu código')
        response = self.client.post(
            response.request['PATH_INFO'] + '?' + response.request['QUERY_STRING'],
            {
                'username': self.cliente.email,
                'password': 'Clave-segura-2026!',
                'next': url_codigo,
            },
        )
        self.assertRedirects(response, url_codigo)
        response = self.client.get(url_codigo)
        self.assertContains(response, 'Generar un código nuevo')

        response = self.client.post(url_codigo, follow=True)
        self.assertContains(response, 'Guarda tu código')
        self.assertRegex(response.context['codigo'], r'^[0-9]{8}$')

    def test_recuperacion_envia_codigo_temporal_al_correo_de_la_cuenta(self):
        response = self.client.get(reverse('recuperar'))
        self.assertContains(response, 'vence en 10 minutos')

        response = self.client.post(
            reverse('recuperar'),
            {'email': self.cliente.email},
            follow=True,
        )

        self.assertContains(response, 'Ingresa tu código')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.cliente.email])
        self.assertIn('restablecer tu contraseña', mail.outbox[0].subject)
        codigo = re.search(r'\b[0-9]{8}\b', mail.outbox[0].body).group()
        self.assertEqual(mail.outbox[0].alternatives[0][1], 'text/html')
        self.assertIn('Prisma', mail.outbox[0].alternatives[0][0])
        self.assertIn(codigo, mail.outbox[0].alternatives[0][0])
        html_body = unescape(mail.outbox[0].alternatives[0][0])
        self.assertIn('Continuar con mi código', html_body)
        self.assertIn('logo_prisma.png', html_body)
        link_match = re.search(
            r'href="([^"]+/recuperar/codigo/continuar/#([^"]+))"',
            html_body,
        )
        self.assertIsNotNone(link_match)
        link = urlsplit(link_match.group(1))
        link_values = parse_qs(link.fragment)
        self.assertEqual(link_values['email'], [self.cliente.email])
        self.assertEqual(link_values['code'], [codigo])
        inline_images = [
            part for part in mail.outbox[0].message(policy=email_policy.default).walk()
            if part.get_content_maintype() == 'image'
        ]
        self.assertEqual(len(inline_images), 0)
        self.assertNotIn('mantén presionado el código', html_body)
        self.cliente.refresh_from_db()
        self.assertTrue(check_password(codigo, self.cliente.email_recovery_code_hash))
        self.assertGreater(self.cliente.email_recovery_code_expires_at, timezone.now())

    def test_enlace_del_correo_verifica_codigo_sin_sesion_previa(self):
        response = self.client.post(
            reverse('recuperar'),
            {'email': self.cliente.email},
        )
        self.assertRedirects(response, reverse('recuperar_codigo'))
        codigo = re.search(r'\b[0-9]{8}\b', mail.outbox[0].body).group()

        response = self.client.get(reverse('recuperar_codigo_email_link'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Verificando tu código')
        self.assertContains(response, 'email_recovery_link.js')

        response = self.client.post(
            reverse('recuperar_codigo'),
            {'recovery_email': self.cliente.email, 'code': codigo},
        )

        self.assertRedirects(response, reverse('recuperar_nueva_contrasena'))
        self.assertNotIn('recovery_email', self.client.session)
        self.assertEqual(self.client.session['password_reset_user_id'], self.cliente.pk)

    def test_recuperacion_no_revela_si_el_correo_no_existe(self):
        response = self.client.post(
            reverse('recuperar'),
            {'email': 'nadie@example.com'},
            follow=True,
        )

        self.assertContains(response, 'Ingresa tu código')
        self.assertEqual(len(mail.outbox), 0)

    def test_recuperacion_no_envia_correo_para_cuentas_administrativas(self):
        response = self.client.post(
            reverse('recuperar'),
            {'email': self.administrador.email},
            follow=True,
        )

        self.assertContains(response, 'Ingresa tu código')
        self.assertEqual(len(mail.outbox), 0)

    def test_recuperacion_administrativa_envia_codigo_solo_al_correo_admin(self):
        response = self.client.get(reverse('login'))
        self.assertContains(response, reverse('admin_recuperar'))

        response = self.client.post(
            reverse('admin_recuperar'),
            {'email': self.administrador.email},
        )

        self.assertRedirects(response, reverse('admin_recuperar_codigo'))
        self.assertEqual(len(mail.outbox), 1)
        mensaje = mail.outbox[0]
        self.assertEqual(mensaje.to, [self.administrador.email])
        self.assertIn('administrativo', mensaje.subject)
        self.assertEqual(mensaje.alternatives[0][1], 'text/html')
        html_body = unescape(mensaje.alternatives[0][0])
        codigo = re.search(r'\b[0-9]{8}\b', mensaje.body).group()
        self.assertIn(codigo, html_body)
        self.assertIn('Acceso administrativo', html_body)
        self.assertIn('Prisma', html_body)
        self.assertIn('logo_prisma.png', html_body)
        self.assertNotIn('Continuar con mi código', html_body)
        self.assertEqual(self.client.session['admin_recovery_email'], self.administrador.email)
        self.assertNotIn('recovery_email', self.client.session)

        response = self.client.get(reverse('admin_recuperar_codigo'))
        self.assertContains(response, 'código de 8 dígitos enviado al correo')
        response = self.client.post(
            reverse('admin_recuperar_codigo'),
            {'code': codigo},
        )
        self.assertRedirects(
            response,
            reverse('admin_recuperar_nueva_contrasena'),
        )
        self.assertEqual(
            self.client.session['admin_password_reset_user_id'],
            self.administrador.pk,
        )
        self.assertNotIn('password_reset_user_id', self.client.session)

        response = self.client.get(reverse('admin_recuperar_nueva_contrasena'))
        self.assertContains(response, 'proteger el panel administrativo')
        nueva_contrasena = 'Otra-clave-segura-2026!'
        response = self.client.post(
            reverse('admin_recuperar_nueva_contrasena'),
            {
                'new_password1': nueva_contrasena,
                'new_password2': nueva_contrasena,
            },
        )
        self.assertRedirects(response, reverse('login'))
        self.administrador.refresh_from_db()
        self.assertTrue(self.administrador.check_password(nueva_contrasena))
        self.assertEqual(self.administrador.recovery_reset_grant_hash, '')

    def test_recuperacion_administrativa_no_envia_codigo_a_clientes(self):
        response = self.client.post(
            reverse('admin_recuperar'),
            {'email': self.cliente.email},
            follow=True,
        )

        self.assertContains(
            response,
            'Si el correo corresponde a una cuenta administrativa activa',
        )
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(self.client.session.get('admin_password_reset_user_id'))
        self.assertFalse(self.cliente.email_recovery_code_hash)

    def test_recuperacion_administrativa_no_reenvia_un_codigo_vigente(self):
        self.client.post(
            reverse('admin_recuperar'),
            {'email': self.administrador.email},
        )
        self.client.post(
            reverse('admin_recuperar'),
            {'email': self.administrador.email},
        )

        self.assertEqual(len(mail.outbox), 1)

    def test_recuperacion_administrativa_no_acepta_codigo_de_respaldo_de_cliente(self):
        self.administrador.recovery_code_hash = make_password(self.codigo_recuperacion)
        self.administrador.save(update_fields=['recovery_code_hash'])
        self.client.post(
            reverse('admin_recuperar'),
            {'email': self.administrador.email},
        )

        response = self.client.post(
            reverse('admin_recuperar_codigo'),
            {'code': self.codigo_recuperacion},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'El código no es válido')
        self.assertFalse(self.client.session.get('admin_password_reset_user_id'))
        self.administrador.refresh_from_db()
        self.assertEqual(self.administrador.recovery_code_attempts, 1)

    def test_cliente_restablece_contrasena_con_codigo_de_un_solo_uso(self):
        codigo = self.solicitar_codigo_por_correo()

        response = self.client.post(
            reverse('recuperar_codigo'),
            {'code': codigo},
        )
        self.assertRedirects(response, reverse('recuperar_nueva_contrasena'))
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.recovery_code_hash, '')
        self.assertEqual(self.cliente.email_recovery_code_hash, '')
        self.assertIsNone(self.cliente.email_recovery_code_expires_at)
        self.assertTrue(self.cliente.recovery_reset_grant_hash)

        response = self.client.get(reverse('recuperar_nueva_contrasena'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Crea tu nueva contraseña')

        response = self.client.post(reverse('recuperar_nueva_contrasena'), {
            'new_password1': 'Otra-clave-mas-segura-2026!',
            'new_password2': 'Otra-clave-mas-segura-2026!',
        })
        self.assertRedirects(response, reverse('login'))

        self.cliente.refresh_from_db()
        self.assertTrue(self.cliente.check_password('Otra-clave-mas-segura-2026!'))
        self.assertEqual(self.cliente.recovery_reset_grant_hash, '')
        self.assertFalse(self.client.session.get('password_reset_nonce'))

        response = self.client.post(
            reverse('recuperar_codigo'),
            {'code': codigo},
        )
        self.assertRedirects(response, reverse('recuperar'))
        self.cliente.refresh_from_db()
        self.assertTrue(self.cliente.check_password('Otra-clave-mas-segura-2026!'))

    def test_codigo_de_respaldo_guardado_tambien_sigue_funcionando(self):
        self.client.post(reverse('recuperar'), {'email': self.cliente.email})

        response = self.client.post(
            reverse('recuperar_codigo'),
            {'code': self.codigo_recuperacion},
        )

        self.assertRedirects(response, reverse('recuperar_nueva_contrasena'))

    def test_codigo_se_bloquea_despues_de_cinco_intentos_incorrectos(self):
        codigo = self.solicitar_codigo_por_correo()

        for intento in range(5):
            with self.subTest(intento=intento + 1):
                response = self.client.post(
                    reverse('recuperar_codigo'),
                    {
                        'code': '00000000'
                        if codigo != '00000000'
                        else '11111111'
                    },
                )
                self.assertEqual(response.status_code, 200)

        self.cliente.refresh_from_db()
        self.assertTrue(check_password(
            codigo,
            self.cliente.email_recovery_code_hash,
        ))
        self.assertEqual(self.cliente.recovery_code_attempts, 5)
        self.assertGreater(self.cliente.recovery_code_locked_until, timezone.now())
        response = self.client.post(
            reverse('recuperar_codigo'),
            {'code': codigo},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('password_reset_user_id', self.client.session)

    def test_codigo_bloqueado_se_puede_usar_tras_quince_minutos(self):
        codigo = self.solicitar_codigo_por_correo()
        Usuario.objects.filter(pk=self.cliente.pk).update(
            recovery_code_attempts=5,
            recovery_code_locked_until=timezone.now() - timedelta(seconds=1),
            email_recovery_code_expires_at=timezone.now() + timedelta(minutes=1),
        )

        response = self.client.post(
            reverse('recuperar_codigo'),
            {'code': codigo},
        )

        self.assertRedirects(response, reverse('recuperar_nueva_contrasena'))
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.recovery_code_hash, '')
        self.assertIsNone(self.cliente.recovery_code_locked_until)

    def test_codigo_de_correo_vencido_no_puede_restablecer_contrasena(self):
        codigo = self.solicitar_codigo_por_correo()
        Usuario.objects.filter(pk=self.cliente.pk).update(
            email_recovery_code_expires_at=timezone.now() - timedelta(seconds=1),
        )

        response = self.client.post(
            reverse('recuperar_codigo'),
            {'code': codigo},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('password_reset_user_id', self.client.session)
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.recovery_reset_grant_hash, '')

    def test_autorizacion_temporal_para_crear_contrasena_tambien_caduca(self):
        self.client.post(reverse('recuperar'), {'email': self.cliente.email})
        self.client.post(
            reverse('recuperar_codigo'),
            {'code': re.search(r'\b[0-9]{8}\b', mail.outbox[-1].body).group()},
        )
        Usuario.objects.filter(pk=self.cliente.pk).update(
            recovery_reset_grant_expires_at=timezone.now() - timedelta(seconds=1),
        )

        response = self.client.get(reverse('recuperar_nueva_contrasena'))

        self.assertRedirects(response, reverse('recuperar'))
        self.cliente.refresh_from_db()
        self.assertTrue(self.cliente.check_password('Clave-segura-2026!'))

    def test_pantallas_de_recuperacion_tienen_diseno_con_imagen_lateral_y_codigo(self):
        response = self.client.get(reverse('recuperar'))
        self.assertContains(response, 'customer-recovery-container')
        self.assertContains(response, 'Continuar')
        self.assertContains(response, 'logo_prisma.png')

        self.client.post(reverse('recuperar'), {'email': self.cliente.email})
        response = self.client.get(reverse('recuperar_codigo'))
        self.assertContains(response, 'código de verificación que enviamos')

    def test_cliente_puede_generar_y_ver_su_codigo_una_sola_vez_con_sesion(self):
        self.client.force_login(self.cliente)
        response = self.client.get(reverse('codigo_recuperacion_cuenta'))
        self.assertContains(response, 'Generar un código nuevo')
        self.assertNotContains(response, self.codigo_recuperacion)
        self.assertIn('no-store', response['Cache-Control'])

        response = self.client.post(
            reverse('codigo_recuperacion_cuenta'),
            follow=True,
        )
        self.assertContains(response, 'Guarda tu código')
        codigo_generado = response.context['codigo']
        self.assertRegex(codigo_generado, r'^[0-9]{8}$')
        self.assertContains(response, 'recovery-code-card')
        self.assertContains(response, 'Copiar código')
        self.assertContains(response, 'tomar una captura')
        self.assertNotIn('codigo_recuperacion_mostrar', self.client.session)

        response = self.client.get(reverse('codigo_recuperacion_cuenta'))
        self.assertNotContains(response, codigo_generado)
        self.cliente.refresh_from_db()
        self.assertTrue(check_password(codigo_generado, self.cliente.recovery_code_hash))
        self.assertFalse(check_password(self.codigo_recuperacion, self.cliente.recovery_code_hash))

    def test_administrador_no_puede_generar_codigo_de_recuperacion_de_cliente(self):
        self.client.force_login(self.administrador)

        response = self.client.get(reverse('codigo_recuperacion_cuenta'))

        self.assertRedirects(response, reverse('perfil'))
        self.administrador.refresh_from_db()
        self.assertEqual(self.administrador.recovery_code_hash, '')

    def test_rechaza_contrasena_incorrecta_y_accesos_cruzados(self):
        for email in (self.administrador.email, self.cliente.email):
            with self.subTest(email=email):
                response = self.client.post(
                    reverse('login'),
                    {'username': email, 'password': 'incorrecta'},
                )
                self.assertEqual(response.status_code, 200)
                self.assertFalse(response.context['form'].is_valid())

    def test_login_unificado_redirige_cada_rol_a_su_panel(self):
        response_cliente = self.client.post(
            reverse('login'),
            {'username': self.cliente.email, 'password': 'Clave-segura-2026!'},
        )
        self.assertRedirects(response_cliente, reverse('base_cliente'))
        self.client.logout()

        response_admin = self.client.post(
            reverse('login'),
            {
                'username': self.administrador.username.upper(),
                'password': 'Clave-segura-2026!',
            },
        )
        self.assertRedirects(response_admin, reverse('perfil'))
        self.assertTrue(self.client.session.get_expire_at_browser_close())

    def test_cliente_sin_staff_no_puede_abrir_panel_ni_categorias(self):
        self.client.force_login(self.cliente)

        for url_name in ('perfil', 'gestion_categorias_insumos'):
            with self.subTest(url=url_name):
                response = self.client.get(reverse(url_name))
                self.assertRedirects(
                    response,
                    f'{reverse("login")}?next={reverse(url_name)}',
                    fetch_redirect_response=False,
                )

    def test_lista_de_usuarios_usa_el_diseno_compartido_del_panel(self):
        self.client.force_login(self.administrador)

        response = self.client.get(reverse('Lista de usuarios'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'insumo-dashboard user-admin-page')
        self.assertContains(response, 'class="admin-page-heading"')
        self.assertContains(response, 'admin-crud-workspace')
        self.assertContains(response, 'admin-crud-sidebar insumo-sidebar')
        self.assertContains(response, 'class="admin-crud-main insumo-main-panel"')
        self.assertContains(response, 'class="insumo-row insumo-row--record')
        self.assertContains(response, self.cliente.username)
        self.assertContains(response, self.cliente.email)
        self.assertContains(response, 'css/admin_crud.css')
        self.assertContains(response, '2 usuarios')
        self.assertContains(response, '2 usuarios activos')
        self.assertContains(response, 'Sin rol asignado')
        self.assertNotContains(response, 'Cambiar rol')
        self.assertNotContains(response, 'css/Lista_usuarios.css')
        self.assertEqual(response.content.count(b'css/admin_panel.css'), 1)
        self.assertEqual(response.content.count(b'css/admin_crud.css'), 1)
        self.assertNotContains(response, 'class="empty-state"')

    def test_registro_rechaza_nombres_con_simbolos_y_telefono_no_numerico(self):
        for first_name, telefono in (
            ('Cl4ra', '3111234567'),
            ('Clara', '+57 3111234567'),
        ):
            with self.subTest(first_name=first_name, telefono=telefono):
                response = self.client.post(
                    reverse('registro'),
                    {
                        'first_name': first_name,
                        'last_name': 'Pérez',
                        'email': f'{first_name.lower()}@example.com',
                        'telefono': telefono,
                        'password1': 'Fuerte-password-2026!',
                        'password2': 'Fuerte-password-2026!',
                    },
                )
                self.assertEqual(response.status_code, 200)
                self.assertFalse(response.context['form'].is_valid())

    def test_registro_crea_usuario_interno_distinto_para_nombres_repetidos(self):
        Usuario.objects.create_user(
            username='mariajose.garcialuna',
            email='primera@example.com',
            telefono='3111234567',
            password='Fuerte-password-2026!',
        )
        datos = {
            'first_name': 'María José',
            'last_name': 'García Luna',
            'email': 'segunda@example.com',
            'telefono': '3111234568',
            'password1': 'Fuerte-password-2026!',
            'password2': 'Fuerte-password-2026!',
        }
        form = RegistroForm(data=datos)

        self.assertTrue(form.is_valid(), form.errors)
        usuario = form.save()

        self.assertEqual(usuario.username, 'mariajose.garcialuna1')
        self.assertEqual(usuario.first_name, 'María José')
        self.assertEqual(usuario.last_name, 'García Luna')

    def test_registro_activa_cuenta_sin_mostrar_codigo_de_respaldo(self):
        response = self.client.post(
            reverse('registro'),
            {
                'first_name': 'María José',
                'last_name': 'García Luna',
                'email': 'nueva@example.com',
                'telefono': '3111234567',
                'password1': 'Fuerte-password-2026!',
                'password2': 'Fuerte-password-2026!',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'],
            reverse('base_cliente'),
        )
        usuario = Usuario.objects.get(email='nueva@example.com')
        self.assertTrue(usuario.is_active)
        self.assertFalse(usuario.is_staff)
        rol_cliente = Group.objects.get(name='Cliente')
        self.assertEqual(list(usuario.groups.all()), [rol_cliente])
        self.assertFalse(rol_cliente.permissions.exists())
        self.assertEqual(usuario.first_name, 'María José')
        self.assertEqual(usuario.last_name, 'García Luna')
        self.assertEqual(usuario.username, 'mariajose.garcialuna')
        self.assertEqual(usuario.recovery_code_hash, '')
        self.assertNotIn('codigo_recuperacion_mostrar', self.client.session)
        self.assertEqual(
            self.client.session['_auth_user_id'],
            str(usuario.pk),
        )
        response = self.client.get(reverse('gestion_insumos'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])

    def test_registro_no_muestra_codigo_y_permite_cerrar_sesion_desde_inicio(self):
        response = self.client.post(
            reverse('registro'),
            {
                'first_name': 'María José',
                'last_name': 'García Luna',
                'email': 'nueva@example.com',
                'telefono': '3111234567',
                'password1': 'Fuerte-password-2026!',
                'password2': 'Fuerte-password-2026!',
            },
            follow=True,
        )

        self.assertRedirects(response, reverse('base_cliente'))
        self.assertContains(response, 'Tu cuenta Prisma está lista. ¡Bienvenido!')
        self.assertNotContains(response, 'Guarda tu código')
        self.assertNotIn('codigo_recuperacion_mostrar', self.client.session)
        usuario = Usuario.objects.get(email='nueva@example.com')
        self.assertEqual(usuario.recovery_code_hash, '')

        response = self.client.get(reverse('login'))
        self.assertRedirects(response, reverse('base_cliente'))
        self.assertEqual(
            self.client.session['_auth_user_id'],
            str(Usuario.objects.get(email='nueva@example.com').pk),
        )

        response = self.client.post(reverse('logout'), follow=True)
        self.assertRedirects(response, reverse('base_cliente'))
        self.assertContains(response, 'Has cerrado sesión correctamente.')
        self.assertContains(response, 'aria-label="Iniciar sesión"')
        self.assertNotContains(response, 'Código de recuperación</a>')

    def test_registro_muestra_boton_para_ver_y_ocultar_ambas_contrasenas(self):
        response = self.client.get(reverse('registro'))

        self.assertContains(response, 'data-password-toggle', count=2)
        self.assertContains(response, 'fa-eye', count=2)
        self.assertContains(response, 'aria-label="Mostrar contraseña"')


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
            reverse('login'),
            {
                'username': self.administrador.email,
                'password': 'Clave-segura-2026!',
                'remember_me': 'on',
            },
        )
        self.assertRedirects(response, reverse('perfil'))
        self.assertTrue(self.client.session.get_expire_at_browser_close())

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


class GestionRolesUsuariosTests(TestCase):
    def setUp(self):
        self.administrador = Usuario.objects.create_user(
            username='admin',
            email='admin@example.com',
            telefono='3007654321',
            password='Clave-segura-2026!',
            is_staff=True,
        )
        self.usuario = Usuario.objects.create_user(
            username='cliente',
            email='cliente@example.com',
            telefono='3001234567',
            password='Clave-segura-2026!',
        )
        self.client.force_login(self.administrador)

    def test_admin_confirma_eliminacion_de_roles_con_dialogo_del_crud(self):
        rol = Group.objects.create(name='Inventario')

        response = self.client.get(reverse('gestion_roles'))

        self.assertContains(response, 'id="roleDeleteDialog"')
        self.assertContains(response, 'insumo-category-dialog insumo-delete-dialog')
        self.assertContains(response, f'data-role-delete-id="{rol.pk}"')
        self.assertContains(response, 'js/admin_crud.js?v=8')
        self.assertNotContains(response, '<script>\n')
        self.assertNotContains(response, 'onclick="return confirm(')

    def test_rol_cliente_no_se_puede_editar_eliminar_ni_convertir_en_rol_privilegiado(self):
        rol_cliente = Group.objects.get(name='Cliente')
        self.assertFalse(RolForm(data={
            'name': 'Cliente',
            'permissions': [],
        }).is_valid())

        response = self.client.get(
            reverse('gestion_roles'),
            {'editar_rol': rol_cliente.pk},
        )
        self.assertRedirects(response, reverse('gestion_roles'))

        response = self.client.post(
            reverse('gestion_roles'),
            {'accion': 'eliminar_rol', 'rol_id': rol_cliente.pk},
        )
        self.assertRedirects(response, reverse('gestion_roles'))
        self.assertTrue(Group.objects.filter(pk=rol_cliente.pk).exists())
        self.assertFalse(rol_cliente.permissions.exists())

    def test_admin_crea_y_edita_usuarios_desde_el_crud(self):
        rol = Group.objects.create(name='Cajero')
        response = self.client.post(
            reverse('Lista de usuarios'),
            {
                'accion': 'crear_usuario',
                'username': 'gestionado',
                'email': 'GESTIONADO@example.com',
                'telefono': '3112345678',
                'rol': rol.pk,
                'is_active': 'on',
            },
        )

        self.assertRedirects(response, reverse('Lista de usuarios'))
        usuario = Usuario.objects.get(username='gestionado')
        self.assertEqual(usuario.email, 'gestionado@example.com')
        self.assertFalse(usuario.has_usable_password())
        self.assertEqual(list(usuario.groups.all()), [rol])
        self.assertTrue(usuario.is_active)
        self.assertFalse(usuario.is_staff)

        nuevo_rol = Group.objects.create(name='Inventario')
        response = self.client.post(
            reverse('Lista de usuarios'),
            {
                'accion': 'editar_usuario',
                'usuario_id': usuario.pk,
                'username': 'usuario_actualizado',
                'email': 'actualizado@example.com',
                'telefono': '3112345678',
                'rol': nuevo_rol.pk,
            },
        )

        self.assertRedirects(response, reverse('Lista de usuarios'))
        usuario.refresh_from_db()
        self.assertEqual(usuario.username, 'usuario_actualizado')
        self.assertEqual(usuario.email, 'actualizado@example.com')
        self.assertEqual(list(usuario.groups.all()), [nuevo_rol])
        self.assertFalse(usuario.is_active)

    def test_formulario_editar_usuario_no_se_reabre_al_recargar_y_solo_muestra_campos_permitidos(self):
        response_crear = self.client.get(
            reverse('Lista de usuarios'),
            {'modal': 'crear'},
        )
        self.assertTrue(response_crear.context['form']['is_active'].value())
        self.assertContains(response_crear, 'crud-editor-availability user-editor-availability')
        self.assertContains(response_crear, 'insumo-availability-control')
        self.assertContains(response_crear, 'Usuario activo')
        self.assertContains(response_crear, 'Usuario inactivo')

        self.usuario.is_active = False
        self.usuario.save(update_fields=['is_active'])
        response = self.client.get(
            reverse('Lista de usuarios'),
            {'editar_usuario': self.usuario.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['form']['is_active'].value())
        self.assertContains(
            response,
            'data-clear-query-params="editar_usuario,modal"',
        )
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="telefono"')
        self.assertContains(response, 'name="rol"')
        self.assertNotContains(response, 'name="password1"')
        self.assertNotContains(response, 'name="password2"')
        self.assertNotContains(response, 'name="first_name"')
        self.assertNotContains(response, 'name="last_name"')
        self.assertNotContains(response, 'data-user-role-select')

    def test_admin_activa_desactiva_y_elimina_usuarios(self):
        respuesta = self.client.post(
            reverse('cambiar_estado_usuario', args=[self.usuario.pk]),
            {'activo': 'false'},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.json()['activo'])
        self.usuario.refresh_from_db()
        self.assertFalse(self.usuario.is_active)

        respuesta = self.client.post(
            reverse('cambiar_estado_usuario', args=[self.usuario.pk]),
            {'activo': 'true'},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.json()['activo'])
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.is_active)

        respuesta = self.client.post(
            reverse('eliminar_usuario', args=[self.usuario.pk]),
        )

        self.assertRedirects(respuesta, reverse('Lista de usuarios'))
        self.assertFalse(Usuario.objects.filter(pk=self.usuario.pk).exists())

    def test_admin_no_puede_desactivarse_ni_eliminarse(self):
        respuesta_estado = self.client.post(
            reverse('cambiar_estado_usuario', args=[self.administrador.pk]),
            {'activo': 'false'},
        )
        respuesta_eliminar = self.client.post(
            reverse('eliminar_usuario', args=[self.administrador.pk]),
        )

        self.assertEqual(respuesta_estado.status_code, 403)
        self.assertEqual(respuesta_eliminar.status_code, 403)
        self.administrador.refresh_from_db()
        self.assertTrue(self.administrador.is_active)

    def test_admin_asigna_cambia_y_quita_el_rol_de_un_usuario(self):
        rol_anterior = Group.objects.create(name='Cajero')
        rol_nuevo = Group.objects.create(name='Inventario')
        self.usuario.groups.add(rol_anterior)

        response = self.client.get(reverse('Lista de usuarios'))
        self.assertContains(response, 'Cajero')
        self.assertNotContains(response, 'Cambiar rol')
        self.assertNotContains(response, 'data-user-role-select')

        response = self.client.get(
            reverse('Lista de usuarios'),
            {'editar_usuario': self.usuario.pk},
        )
        self.assertContains(response, 'name="rol"')
        self.assertContains(response, f'<option value="{rol_anterior.pk}" selected')

        response = self.client.post(
            reverse('Lista de usuarios'),
            {
                'accion': 'editar_usuario',
                'usuario_id': self.usuario.pk,
                'username': self.usuario.username,
                'email': self.usuario.email,
                'telefono': self.usuario.telefono,
                'rol': rol_nuevo.pk,
            },
        )
        self.assertRedirects(response, reverse('Lista de usuarios'))
        self.assertEqual(list(self.usuario.groups.all()), [rol_nuevo])

        response = self.client.post(
            reverse('Lista de usuarios'),
            {'usuario_id': self.usuario.pk, 'rol': ''},
        )
        self.assertRedirects(response, reverse('Lista de usuarios'))
        self.assertFalse(self.usuario.groups.exists())

    def test_admin_no_puede_cambiar_su_propio_rol(self):
        rol = Group.objects.create(name='Administración')

        response = self.client.post(
            reverse('Lista de usuarios'),
            {'usuario_id': self.administrador.pk, 'rol': rol.pk},
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.administrador.groups.exists())

    def test_admin_crea_edita_y_elimina_roles_con_permisos(self):
        permiso = Permission.objects.filter(
            content_type__app_label='usuarios',
        ).first()
        self.assertIsNotNone(permiso)

        response = self.client.post(
            reverse('gestion_roles'),
            {
                'accion': 'crear_rol',
                'name': 'Gestor de usuarios',
                'permissions': [permiso.pk],
            },
        )
        self.assertRedirects(response, reverse('gestion_roles'))
        rol = Group.objects.get(name='Gestor de usuarios')
        self.assertEqual(list(rol.permissions.all()), [permiso])

        response = self.client.get(
            reverse('gestion_roles'),
            {'editar_rol': rol.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Editar rol')

        self.client.post(
            reverse('gestion_roles'),
            {
                'accion': 'editar_rol',
                'rol_id': rol.pk,
                'name': 'Gestor actualizado',
                'permissions': [permiso.pk],
            },
        )
        rol.refresh_from_db()
        self.assertEqual(rol.name, 'Gestor actualizado')

        self.usuario.groups.add(rol)
        response = self.client.post(
            reverse('gestion_roles'),
            {'accion': 'eliminar_rol', 'rol_id': rol.pk},
        )
        self.assertRedirects(response, reverse('gestion_roles'))
        self.assertFalse(Group.objects.filter(pk=rol.pk).exists())
        self.assertFalse(self.usuario.groups.exists())

    def test_cliente_no_puede_asignar_roles_ni_abrir_su_crud(self):
        self.client.force_login(self.usuario)
        roles_url = reverse('gestion_roles')
        users_url = reverse('Lista de usuarios')

        for url in (roles_url, users_url):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    f'{reverse("login")}?next={url}',
                    fetch_redirect_response=False,
                )

        response = self.client.post(
            users_url,
            {'usuario_id': self.usuario.pk, 'rol': ''},
        )
        self.assertRedirects(
            response,
            f'{reverse("login")}?next={users_url}',
            fetch_redirect_response=False,
        )


class PermisosPorRolTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='gestor_productos',
            email='gestor@example.com',
            telefono='3001234567',
            password='Clave-segura-2026!',
        )
        self.rol = Group.objects.create(name='Gestor de productos')
        permisos_productos = Permission.objects.filter(
            content_type__app_label='productos',
            content_type__model='producto',
        )
        self.rol.permissions.set(permisos_productos)
        self.usuario.groups.add(self.rol)
        self.client.force_login(self.usuario)

    def test_usuario_con_rol_sin_is_staff_inicia_sesion_y_solo_accede_a_sus_modulos(self):
        self.client.logout()
        response = self.client.post(
            reverse('login'),
            {
                'username': self.usuario.email,
                'password': 'Clave-segura-2026!',
            },
        )

        self.assertRedirects(response, reverse('perfil'))
        self.assertEqual(self.client.get(reverse('lista_productos')).status_code, 200)
        self.assertEqual(self.client.get(reverse('gestion_proveedores')).status_code, 403)
        self.assertEqual(self.client.get(reverse('gestion_insumos')).status_code, 403)
        self.assertEqual(self.client.get(reverse('Lista de usuarios')).status_code, 403)

    def test_rol_de_productos_no_abre_otros_cruds_y_paneles_quedan_bloqueados(self):
        self.assertEqual(
            self.client.get(reverse('lista_productos')).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse('crear_producto')).status_code,
            200,
        )

        for route in (
            'gestion_proveedores',
            'gestion_insumos',
            'Lista de usuarios',
            'gestion_roles',
        ):
            with self.subTest(route=route):
                self.assertEqual(
                    self.client.get(reverse(route)).status_code,
                    403,
                )

        dashboard = self.client.get(reverse('perfil'))
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(
            dashboard,
            'href="/productos/lista_productos/"',
        )
        self.assertContains(
            dashboard,
            'class="quick-action dashboard-module-blocked"',
        )
        self.assertContains(dashboard, 'Tu rol no tiene permiso para consultar reservas.')
        self.assertContains(dashboard, 'Tu rol no tiene permiso para consultar compras.')
        self.assertContains(dashboard, 'class="dashboard-section dashboard-module-blocked" id="inventario"')

    def test_permisos_de_producto_no_habilitan_operaciones_de_otros_modulos(self):
        proveedor = Proveedor.objects.create(nombre='Proveedor confidencial')

        response = self.client.post(
            reverse('cambiar_estado_proveedor', args=[proveedor.pk]),
            {'activo': 'false'},
        )

        self.assertEqual(response.status_code, 403)
        proveedor.refresh_from_db()
        self.assertTrue(proveedor.activo)

    def test_superusuario_con_rol_usa_permisos_del_rol_en_vez_del_bypass_de_django(self):
        self.usuario.is_superuser = True
        self.usuario.save(update_fields=['is_superuser'])
        self.assertTrue(self.usuario.has_perm('proveedores.view_proveedor'))

        self.assertEqual(
            self.client.get(reverse('lista_productos')).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse('gestion_proveedores')).status_code,
            403,
        )

        dashboard = self.client.get(reverse('perfil'))
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(
            dashboard,
            'href="/productos/lista_productos/"',
        )
        self.assertContains(
            dashboard,
            'Tu rol no permite gestionar proveedores.',
        )

    def test_usuario_con_permiso_de_gestion_no_puede_cambiar_su_propio_rol(self):
        permiso = Permission.objects.get(
            content_type__app_label='usuarios',
            content_type__model='usuario',
            codename='change_usuario',
        )
        self.rol.permissions.add(permiso)

        response = self.client.post(
            reverse('Lista de usuarios'),
            {'usuario_id': self.usuario.pk, 'rol': ''},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(list(self.usuario.groups.all()), [self.rol])

    def test_cambiar_rol_requiere_permiso_explicito_de_cambiar_grupos(self):
        permisos_usuarios = Permission.objects.filter(
            content_type__app_label='usuarios',
            content_type__model='usuario',
            codename__in=['view_usuario', 'change_usuario'],
        )
        self.rol.permissions.add(*permisos_usuarios)
        rol_anterior = Group.objects.create(name='Rol anterior')
        objetivo = Usuario.objects.create_user(
            username='objetivo',
            email='objetivo@example.com',
            telefono='3001112233',
            password='Clave-segura-2026!',
        )
        objetivo.groups.add(rol_anterior)

        response = self.client.post(
            reverse('Lista de usuarios'),
            {'usuario_id': objetivo.pk, 'rol': self.rol.pk},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(list(objetivo.groups.all()), [rol_anterior])
