from django.test import TestCase
from django.urls import reverse

from APP.inventario.models import Movimiento
from APP.insumos.models import CategoriaInsumo, Insumo
from APP.proveedores.models import Proveedor
from APP.usuarios.models import Usuario


class GestionInsumosTests(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            username='admin-insumos',
            email='admin-insumos@example.com',
            password='Clave-segura-2026!',
            telefono='3001234567',
            is_staff=True,
        )
        self.cliente = Usuario.objects.create_user(
            username='cliente-insumos',
            email='cliente-insumos@example.com',
            password='Clave-segura-2026!',
            telefono='3007654321',
        )
        self.categoria = CategoriaInsumo.objects.create(
            nombre='Lácteos',
            descripcion='Ingredientes refrigerados',
        )
        self.proveedor = Proveedor.objects.create(
            nombre='Proveedor de prueba',
            telefono='3001112233',
        )
        self.insumo = Insumo.objects.create(
            nombre='Leche entera',
            descripcion='Leche fresca',
            categoria=self.categoria,
            proveedor_referencia=self.proveedor,
            unidad_medida='l',
        )
        self.client.force_login(self.admin)
        self.url = reverse('gestion_insumos')

    def test_admin_ve_panel_con_categorias_lista_y_filtros(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gestión de insumos')
        self.assertContains(response, 'Lácteos')
        self.assertNotContains(response, 'data-insumo-row=')
        self.assertContains(response, 'Buscar por')
        self.assertContains(response, 'Nombre')
        self.assertContains(response, 'Tipo')
        self.assertContains(response, 'Tamaño')
        self.assertContains(response, 'Encuentra un insumo')
        self.assertContains(response, 'Proveedores')

    def test_busqueda_categoria_y_estado_filtran_la_lista(self):
        otra_categoria = CategoriaInsumo.objects.create(nombre='Limpieza')
        Insumo.objects.create(
            nombre='Detergente',
            categoria=otra_categoria,
            unidad_medida='u',
        )

        response = self.client.get(
            self.url,
            {
                'categoria': self.categoria.pk,
                'q': 'leche',
                'campo': 'nombre',
                'estado': 'activos',
            },
        )
        self.assertEqual(
            list(response.context['insumos']),
            [self.insumo],
        )

        self.insumo.activo = False
        self.insumo.save(update_fields=['activo'])
        response = self.client.get(self.url, {'estado': 'inactivos'})
        self.assertEqual(list(response.context['insumos']), [self.insumo])

    def test_categoria_seleccionada_muestra_su_formulario_de_edicion(self):
        response = self.client.get(self.url, {'categoria': self.categoria.pk})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Editar categoría')
        self.assertContains(response, 'name="accion" value="editar_categoria"')
        self.assertContains(
            response,
            f'name="categoria-{self.categoria.pk}-nombre"',
        )
        self.assertEqual(
            response.context['editar_categoria_form'].instance,
            self.categoria,
        )

    def test_busca_por_tipo_y_tamano(self):
        response = self.client.get(
            self.url,
            {'q': 'láct', 'campo': 'tipo'},
        )
        self.assertEqual(list(response.context['insumos']), [self.insumo])

        response = self.client.get(
            self.url,
            {'q': 'litro', 'campo': 'tamano'},
        )
        self.assertEqual(list(response.context['insumos']), [self.insumo])

        response = self.client.get(
            self.url,
            {'q': 'oz', 'campo': 'tamano'},
        )
        self.assertEqual(list(response.context['insumos']), [])

    def test_busqueda_muestra_resultados_solo_despues_de_filtrar(self):
        response = self.client.get(self.url)
        self.assertFalse(response.context['mostrar_resultados'])

        response = self.client.get(self.url, {'q': 'leche', 'campo': 'nombre'})
        self.assertTrue(response.context['mostrar_resultados'])
        self.assertContains(response, 'Leche entera')

    def test_categoria_no_abre_detalle_hasta_pulsar_la_flecha(self):
        response = self.client.get(self.url, {'categoria': self.categoria.pk})

        self.assertContains(response, 'id="insumoDialog"')
        self.assertContains(
            response,
            f'data-insumo-url="{reverse("detalle_insumo", args=[self.insumo.pk])}"',
        )
        self.assertNotContains(response, '?insumo=')
        self.assertNotContains(response, 'insumo-row-image')

    def test_detalle_insumo_entrega_datos_para_la_ficha_modal(self):
        response = self.client.get(reverse('detalle_insumo', args=[self.insumo.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['nombre'], 'Leche entera')
        self.assertEqual(response.json()['categoria'], 'Lácteos')
        self.assertEqual(
            response.json()['proveedor_referencia'],
            self.proveedor.nombre,
        )
        self.assertTrue(response.json()['activo'])
        self.assertIn({'id': 'l', 'nombre': 'Litro'}, response.json()['unidades'])

    def test_modal_actualiza_y_desactiva_insumo_sin_perder_historial(self):
        url = reverse('detalle_insumo', args=[self.insumo.pk])
        response = self.client.post(url, {
            'accion': 'editar_insumo',
            f'insumo-{self.insumo.pk}-nombre': 'Leche deslactosada',
            f'insumo-{self.insumo.pk}-descripcion': 'Leche fresca',
            f'insumo-{self.insumo.pk}-categoria': self.categoria.pk,
            f'insumo-{self.insumo.pk}-proveedor_referencia': self.proveedor.pk,
            f'insumo-{self.insumo.pk}-unidad_medida': 'l',
            f'insumo-{self.insumo.pk}-activo': 'on',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['nombre'], 'Leche deslactosada')
        self.assertEqual(
            response.json()['proveedor_referencia_id'],
            self.proveedor.pk,
        )

        response = self.client.post(
            url,
            {'accion': 'cambiar_disponibilidad', 'activo': 'false'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['activo'])
        self.insumo.refresh_from_db()
        self.assertFalse(self.insumo.activo)
        self.assertTrue(Insumo.objects.filter(pk=self.insumo.pk).exists())

    def test_eliminar_insumo_sin_historial_lo_elimina(self):
        response = self.client.post(
            reverse('detalle_insumo', args=[self.insumo.pk]),
            {'accion': 'eliminar_insumo'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['deleted'])
        self.assertFalse(Insumo.objects.filter(pk=self.insumo.pk).exists())

    def test_eliminar_insumo_con_movimientos_recientes_se_bloquea(self):
        Movimiento.objects.create(
            origen='AJUSTE',
            accion='ENTRADA',
            usuario=self.admin,
            insumo=self.insumo,
            cantidad='1.000',
            unidad_medida='l',
        )

        response = self.client.post(
            reverse('detalle_insumo', args=[self.insumo.pk]),
            {'accion': 'eliminar_insumo'},
        )

        self.assertEqual(response.status_code, 409)
        self.assertTrue(response.json()['blocked_by_history'])
        self.assertTrue(Insumo.objects.filter(pk=self.insumo.pk).exists())

    def test_crear_insumo_exige_proveedor_y_guarda_categoria_y_unidad(self):
        response = self.client.post(
            self.url,
            {
                'accion': 'crear_insumo',
                'nombre': 'Crema',
                'descripcion': 'Crema de leche',
                'categoria': self.categoria.pk,
                'unidad_medida': 'ml',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Insumo.objects.filter(nombre='Crema').exists())
        self.assertContains(response, 'Selecciona el proveedor de referencia.')

        response = self.client.post(
            self.url,
            {
                'accion': 'crear_insumo',
                'nombre': 'Crema',
                'descripcion': 'Crema de leche',
                'categoria': self.categoria.pk,
                'proveedor_referencia': self.proveedor.pk,
                'unidad_medida': 'ml',
            },
        )

        crema = Insumo.objects.get(nombre='Crema')
        self.assertEqual(crema.categoria, self.categoria)
        self.assertEqual(crema.proveedor_referencia, self.proveedor)
        self.assertEqual(crema.unidad_medida, 'ml')
        self.assertRedirects(
            response,
            f'{self.url}?categoria={self.categoria.pk}',
        )

    def test_cliente_no_puede_consultar_ni_modificar_detalle_insumo(self):
        self.client.force_login(self.cliente)

        response = self.client.get(reverse('detalle_insumo', args=[self.insumo.pk]))

        self.assertRedirects(
            response,
            f'{reverse("admin_login")}?next={reverse("detalle_insumo", args=[self.insumo.pk])}',
        )
        response = self.client.post(
            reverse('detalle_insumo', args=[self.insumo.pk]),
            {'accion': 'eliminar_insumo'},
        )
        self.assertEqual(response.status_code, 302)
        self.insumo.refresh_from_db()
        self.assertTrue(self.insumo.activo)

    def test_busqueda_de_categorias_filtra_el_panel_izquierdo(self):
        CategoriaInsumo.objects.create(nombre='Limpieza')

        response = self.client.get(self.url, {'categoria_q': 'láct'})

        self.assertEqual(
            list(response.context['categorias'].values_list('nombre', flat=True)),
            ['Lácteos'],
        )
        self.assertEqual(response.context['total_categorias'], 2)

    def test_crea_edita_y_elimina_categoria_vacia(self):
        response = self.client.post(
            self.url,
            {
                'accion': 'crear_categoria',
                'nombre': 'Frutas',
                'descripcion': 'Frutas frescas',
            },
        )
        categoria = CategoriaInsumo.objects.get(nombre='Frutas')
        self.assertRedirects(
            response,
            f'{self.url}?categoria={categoria.pk}',
        )

        response = self.client.post(
            self.url,
            {
                'accion': 'editar_categoria',
                'categoria_id': categoria.pk,
                f'categoria-{categoria.pk}-nombre': 'Frutas frescas',
                f'categoria-{categoria.pk}-descripcion': 'Fruta de temporada',
            },
        )
        categoria.refresh_from_db()
        self.assertEqual(categoria.nombre, 'Frutas frescas')
        self.assertRedirects(
            response,
            f'{self.url}?categoria={categoria.pk}',
        )

        response = self.client.post(
            self.url,
            {
                'accion': 'eliminar_categoria',
                'categoria_id': categoria.pk,
            },
        )
        self.assertFalse(CategoriaInsumo.objects.filter(pk=categoria.pk).exists())
        self.assertRedirects(response, self.url)

    def test_categoria_con_insumos_no_se_puede_eliminar(self):
        response = self.client.post(
            self.url,
            {
                'accion': 'eliminar_categoria',
                'categoria_id': self.categoria.pk,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain[-1][0], self.url)
        self.assertTrue(CategoriaInsumo.objects.filter(pk=self.categoria.pk).exists())
        self.assertTrue(Insumo.objects.filter(pk=self.insumo.pk).exists())
        self.assertContains(response, 'Mueve o elimina sus insumos primero.')

    def test_crea_edita_y_desactiva_insumo_sin_perderlo(self):
        otra_categoria = CategoriaInsumo.objects.create(nombre='Repostería')
        response = self.client.post(
            self.url,
            {
                'accion': 'crear_insumo',
                'nombre': 'Harina',
                'descripcion': 'Harina de trigo',
                'categoria': otra_categoria.pk,
                'proveedor_referencia': self.proveedor.pk,
                'unidad_medida': 'kg',
            },
        )
        harina = Insumo.objects.get(nombre='Harina')
        self.assertRedirects(
            response,
            f'{self.url}?categoria={otra_categoria.pk}',
        )

        response = self.client.post(
            self.url,
            {
                'accion': 'editar_insumo',
                'insumo_id': harina.pk,
                f'insumo-{harina.pk}-nombre': 'Harina integral',
                f'insumo-{harina.pk}-descripcion': 'Harina integral de trigo',
                f'insumo-{harina.pk}-categoria': otra_categoria.pk,
                f'insumo-{harina.pk}-proveedor_referencia': self.proveedor.pk,
                f'insumo-{harina.pk}-unidad_medida': 'kg',
                f'insumo-{harina.pk}-activo': 'on',
            },
        )
        harina.refresh_from_db()
        self.assertEqual(harina.nombre, 'Harina integral')
        self.assertRedirects(
            response,
            f'{self.url}?categoria={otra_categoria.pk}',
        )

        self.client.post(
            self.url,
            {'accion': 'eliminar_insumo', 'insumo_id': harina.pk},
        )
        harina.refresh_from_db()
        self.assertFalse(harina.activo)

        self.client.post(
            self.url,
            {'accion': 'restaurar_insumo', 'insumo_id': harina.pk},
        )
        harina.refresh_from_db()
        self.assertTrue(harina.activo)

    def test_cliente_no_puede_acceder_al_modulo(self):
        self.client.force_login(self.cliente)

        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            f'{reverse("admin_login")}?next={self.url}',
        )

    def test_ids_invalidos_no_modifican_datos(self):
        response = self.client.post(
            self.url,
            {'accion': 'eliminar_insumo', 'insumo_id': 'no-es-un-id'},
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Insumo.objects.filter(pk=self.insumo.pk).exists())
