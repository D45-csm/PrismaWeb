from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.contrib.auth.models import Group, Permission
from django.test import TestCase, override_settings
from django.conf import settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from APP.insumos.models import CategoriaInsumo, Insumo
from APP.proveedores.models import Proveedor

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

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
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

    def test_lista_de_usuarios_usa_el_diseno_compartido_del_panel(self):
        self.client.force_login(self.administrador)

        response = self.client.get(reverse('Lista de usuarios'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'insumo-dashboard user-admin-page')
        self.assertContains(response, 'class="admin-page-heading"')
        self.assertContains(response, 'admin-crud-workspace--single')
        self.assertContains(response, 'class="admin-crud-main admin-crud-panel"')
        self.assertContains(response, self.cliente.username)
        self.assertContains(response, self.cliente.email)
        self.assertContains(response, 'css/admin_crud.css')
        self.assertContains(response, '2 usuarios')
        self.assertContains(response, '2 usuarios activos')
        self.assertContains(response, 'Rol actual')
        self.assertNotContains(response, 'css/Lista_usuarios.css')
        self.assertEqual(response.content.count(b'css/admin_panel.css'), 1)
        self.assertEqual(response.content.count(b'css/admin_crud.css'), 1)
        self.assertNotContains(response, '</article>')
        self.assertNotContains(response, 'class="empty-state"')

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
        self.assertContains(response, 'js/admin_crud.js?v=4')
        self.assertNotContains(response, '<script>\n')
        self.assertNotContains(response, 'onclick="return confirm(')

    def test_admin_asigna_cambia_y_quita_el_rol_de_un_usuario(self):
        rol_anterior = Group.objects.create(name='Cajero')
        rol_nuevo = Group.objects.create(name='Inventario')
        self.usuario.groups.add(rol_anterior)

        response = self.client.get(reverse('Lista de usuarios'))
        self.assertContains(response, 'Cajero')
        self.assertContains(response, 'Cambiar rol')
        self.assertContains(response, f'<option value="{rol_anterior.pk}" selected')
        self.assertContains(response, 'disabled')
        self.assertContains(response, 'No puedes cambiar tu propio rol.')
        self.assertContains(response, 'data-user-role-save hidden')
        self.assertContains(response, 'js/lista_usuarios.js?v=2')

        response = self.client.post(
            reverse('Lista de usuarios'),
            {'usuario_id': self.usuario.pk, 'rol': rol_nuevo.pk},
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
                    f'{reverse("admin_login")}?next={url}',
                )

        response = self.client.post(
            users_url,
            {'usuario_id': self.usuario.pk, 'rol': ''},
        )
        self.assertRedirects(
            response,
            f'{reverse("admin_login")}?next={users_url}',
        )


class PermisosPorRolTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='gestor_productos',
            email='gestor@example.com',
            telefono='3001234567',
            password='Clave-segura-2026!',
            is_staff=True,
        )
        self.rol = Group.objects.create(name='Gestor de productos')
        permisos_productos = Permission.objects.filter(
            content_type__app_label='productos',
            content_type__model='producto',
        )
        self.rol.permissions.set(permisos_productos)
        self.usuario.groups.add(self.rol)
        self.client.force_login(self.usuario)

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
