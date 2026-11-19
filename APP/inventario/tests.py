from decimal import Decimal

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from APP.insumos.models import CategoriaInsumo, Insumo
from APP.usuarios.models import Usuario

from .models import Movimiento


class InventarioTests(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            username='admin-inventario',
            email='admin-inventario@example.com',
            password='Clave-segura-2026!',
            telefono='3001234567',
            is_staff=True,
        )
        self.categoria = CategoriaInsumo.objects.create(nombre='Ingredientes')
        self.harina = Insumo.objects.create(
            nombre='Harina',
            categoria=self.categoria,
            unidad_medida='kg',
            stock_minimo=Decimal('0.500'),
        )
        self.client.force_login(self.admin)

    def registrar(self, accion, cantidad, unidad='kg'):
        return Movimiento.objects.create(
            origen='AJUSTE',
            accion=accion,
            insumo=self.harina,
            cantidad=Decimal(cantidad),
            unidad_medida=unidad,
        )

    def test_tablero_calcula_stock_convertido_y_resalta_minimo(self):
        self.registrar('ENTRADA', '500.000', 'g')

        response = self.client.get(reverse('inventario_dashboard'))

        self.assertEqual(response.status_code, 200)
        fila = response.context['filas_inventario'][0]
        self.assertEqual(fila['stock'], Decimal('0.5'))
        self.assertTrue(fila['stock_bajo'])
        self.assertContains(response, 'inventory-low-stock')
        self.assertContains(response, 'Stock bajo')
        self.assertContains(response, 'Historial de movimientos')
        self.assertContains(response, 'css/inventario.css?v=3')
        self.assertContains(response, 'js/inventario.js?v=3')

    def test_ajuste_manual_registra_salida_y_aparece_en_historial(self):
        self.registrar('ENTRADA', '2.000')

        response = self.client.post(reverse('inventario_dashboard'), {
            'modo': 'movimiento',
            'insumo': self.harina.pk,
            'tipo_accion': 'SALIDA',
            'cantidad': '1.250',
        })

        self.assertRedirects(response, reverse('inventario_dashboard'))
        movimiento = Movimiento.objects.get(origen='AJUSTE', accion='SALIDA')
        self.assertEqual(movimiento.cantidad, Decimal('1.250'))
        self.assertEqual(movimiento.usuario, self.admin)
        historial = self.client.get(reverse('historial_movimientos'))
        self.assertEqual(
            historial.context['pagina'].object_list[0].cantidad,
            Decimal('1.250'),
        )

    def test_conteo_fisico_registra_solo_la_diferencia(self):
        self.registrar('ENTRADA', '1.000')

        response = self.client.post(reverse('inventario_dashboard'), {
            'modo': 'conteo',
            'insumo': self.harina.pk,
            'tipo_accion': '',
            'cantidad': '0.750',
        })

        self.assertRedirects(response, reverse('inventario_dashboard'))
        movimiento = Movimiento.objects.get(origen='AJUSTE', accion='SALIDA')
        self.assertEqual(movimiento.cantidad, Decimal('0.250'))
        self.assertEqual(movimiento.unidad_medida, 'kg')

    def test_ajuste_rechaza_salidas_mayores_al_stock(self):
        response = self.client.post(reverse('inventario_dashboard'), {
            'modo': 'movimiento',
            'insumo': self.harina.pk,
            'tipo_accion': 'SALIDA',
            'cantidad': '0.500',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'La salida no puede ser mayor')
        self.assertEqual(Movimiento.objects.count(), 0)

    def test_conteo_igual_no_crea_movimiento(self):
        self.registrar('ENTRADA', '1.000')
        response = self.client.post(reverse('inventario_dashboard'), {
            'modo': 'conteo',
            'insumo': self.harina.pk,
            'tipo_accion': '',
            'cantidad': '1.000',
        })

        self.assertRedirects(response, reverse('inventario_dashboard'))
        self.assertEqual(Movimiento.objects.count(), 1)

    def test_usuario_solo_lectura_no_puede_hacer_ajustes(self):
        viewer = Usuario.objects.create_user(
            username='viewer-inventario',
            email='viewer-inventario@example.com',
            password='Clave-segura-2026!',
            telefono='3007654321',
        )
        permiso = Permission.objects.get(
            content_type__app_label='insumos',
            codename='view_insumo',
        )
        viewer.user_permissions.add(permiso)
        self.client.force_login(viewer)

        response = self.client.get(reverse('inventario_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'data-open-inventory-dialog')

        response = self.client.post(reverse('inventario_dashboard'), {
            'modo': 'movimiento',
            'insumo': self.harina.pk,
            'tipo_accion': 'ENTRADA',
            'cantidad': '1.000',
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Movimiento.objects.count(), 0)

    def test_cajas_ya_no_es_unidad_de_movimiento(self):
        self.assertNotIn(
            'cajas',
            [value for value, _label in Movimiento.unidad_medida_choices],
        )

    def test_panel_administrativo_enlaza_al_tablero_de_inventario(self):
        response = self.client.get(reverse('perfil'))

        self.assertContains(
            response,
            f'href="{reverse("inventario_dashboard")}"',
        )

    def test_busqueda_por_categoria_y_filtro_de_stock_bajo(self):
        response = self.client.get(
            reverse('inventario_dashboard'),
            {'q': 'Ingred', 'stock': 'bajo'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [fila['insumo'] for fila in response.context['filas_inventario']],
            [self.harina],
        )
        response = self.client.get(
            reverse('inventario_dashboard'),
            {'q': 'sin coincidencias'},
        )
        self.assertContains(response, 'No se encontraron insumos.')

    def test_pdf_exporta_todo_el_inventario_con_existencias(self):
        self.registrar('ENTRADA', '1.250')

        response = self.client.get(reverse('exportar_inventario_pdf'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn(
            'attachment; filename="reporte_inventario.pdf"',
            response['Content-Disposition'],
        )
        self.assertTrue(response.content.startswith(b'%PDF-'))
        self.assertTrue(response.content.rstrip().endswith(b'%%EOF'))

    def test_anular_movimiento_lo_conserva_y_recalcula_stock(self):
        movimiento = self.registrar('ENTRADA', '2.000')

        response = self.client.post(
            reverse('anular_movimiento', args=[movimiento.pk]),
            {'motivo': 'Registro duplicado'},
        )

        self.assertRedirects(response, reverse('historial_movimientos'))
        movimiento.refresh_from_db()
        self.assertEqual(movimiento.estado, Movimiento.Estado.ANULADO)
        self.assertEqual(movimiento.motivo_anulacion, 'Registro duplicado')
        self.assertEqual(movimiento.anulado_por, self.admin)
        self.assertIsNotNone(movimiento.fecha_anulacion)
        self.assertEqual(Movimiento.objects.count(), 1)

        tablero = self.client.get(reverse('inventario_dashboard'))
        self.assertEqual(
            tablero.context['filas_inventario'][0]['stock'],
            Decimal('0'),
        )
        historial = self.client.get(reverse('historial_movimientos'))
        self.assertContains(historial, 'Registro duplicado')
        self.assertContains(historial, 'Anulado')
        self.assertNotContains(historial, 'data-cancel-movement')

    def test_no_anula_entrada_si_el_stock_ya_fue_consumido(self):
        entrada = self.registrar('ENTRADA', '1.000')
        self.registrar('SALIDA', '0.750')

        response = self.client.post(
            reverse('anular_movimiento', args=[entrada.pk]),
            {'motivo': 'Entrada equivocada'},
        )

        self.assertRedirects(response, reverse('historial_movimientos'))
        entrada.refresh_from_db()
        self.assertEqual(entrada.estado, Movimiento.Estado.ACTIVO)
        self.assertEqual(
            self.client.get(reverse('inventario_dashboard'))
            .context['filas_inventario'][0]['stock'],
            Decimal('0.250'),
        )

    def test_anulacion_requiere_motivo_y_no_se_puede_repetir(self):
        movimiento = self.registrar('ENTRADA', '1.000')

        response = self.client.post(
            reverse('anular_movimiento', args=[movimiento.pk]),
            {'motivo': '  '},
        )
        self.assertRedirects(response, reverse('historial_movimientos'))
        movimiento.refresh_from_db()
        self.assertEqual(movimiento.estado, Movimiento.Estado.ACTIVO)

        self.client.post(
            reverse('anular_movimiento', args=[movimiento.pk]),
            {'motivo': 'Corrección'},
        )
        response = self.client.post(
            reverse('anular_movimiento', args=[movimiento.pk]),
            {'motivo': 'Intento repetido'},
        )
        self.assertRedirects(response, reverse('historial_movimientos'))
        movimiento.refresh_from_db()
        self.assertEqual(movimiento.motivo_anulacion, 'Corrección')

    def test_historial_ofrece_anular_movimientos_activos(self):
        movimiento = self.registrar('SALIDA', '0.250')

        response = self.client.get(reverse('historial_movimientos'))

        self.assertContains(
            response,
            f'action="{reverse("anular_movimiento", args=[movimiento.pk])}"',
        )
        self.assertContains(response, 'data-cancel-movement')
        self.assertContains(response, 'js/inventario.js?v=3')

    def test_usuario_solo_lectura_no_puede_anular_movimientos(self):
        viewer = Usuario.objects.create_user(
            username='viewer-anulacion',
            email='viewer-anulacion@example.com',
            password='Clave-segura-2026!',
            telefono='3005554321',
        )
        permiso = Permission.objects.get(
            content_type__app_label='insumos',
            codename='view_insumo',
        )
        viewer.user_permissions.add(permiso)
        movimiento = self.registrar('ENTRADA', '1.000')
        self.client.force_login(viewer)

        response = self.client.post(
            reverse('anular_movimiento', args=[movimiento.pk]),
            {'motivo': 'Sin permiso'},
        )

        self.assertEqual(response.status_code, 403)
        movimiento.refresh_from_db()
        self.assertEqual(movimiento.estado, Movimiento.Estado.ACTIVO)
