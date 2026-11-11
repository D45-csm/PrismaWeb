from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from APP.inventario.models import Movimiento
from APP.insumos.models import CategoriaInsumo, Insumo

from .models import Receta, RecetaInsumo


class GestionRecetasTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username='admin-recetas',
            password='Clave-segura-2026!',
            telefono='3001234567',
            is_staff=True,
        )
        self.client.force_login(self.admin)
        self.categoria = CategoriaInsumo.objects.create(nombre='Ingredientes')
        self.harina = Insumo.objects.create(
            nombre='Harina',
            categoria=self.categoria,
            unidad_medida='kg',
        )
        self.leche = Insumo.objects.create(
            nombre='Leche',
            categoria=self.categoria,
            unidad_medida='l',
        )

    def datos_receta(self, **overrides):
        datos = {
            'accion': 'crear_receta',
            'nombre': 'Masa básica',
            'descripcion': 'Receta de prueba',
            'activo': 'on',
            'ingredients-TOTAL_FORMS': '1',
            'ingredients-INITIAL_FORMS': '0',
            'ingredients-MIN_NUM_FORMS': '0',
            'ingredients-MAX_NUM_FORMS': '30',
            'ingredients-0-insumo': str(self.harina.pk),
            'ingredients-0-cantidad_insumo': '0.5',
            'ingredients-0-medida_insumo': 'kg',
        }
        datos.update(overrides)
        return datos

    def registrar_stock(self, insumo, cantidad, unidad):
        return Movimiento.objects.create(
            origen='AJUSTE',
            accion='ENTRADA',
            insumo=insumo,
            cantidad=cantidad,
            unidad_medida=unidad,
        )

    def test_crud_recetas_crea_edita_y_elimina_ingredientes_vinculados(self):
        response = self.client.get(reverse('lista_recetas'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gestión de recetas')
        self.assertContains(response, 'Crear receta')
        self.assertContains(response, 'admin-crud-editor-dialog')
        self.assertContains(response, 'css/admin_crud.css')
        self.assertContains(response, 'js/admin_messages.js')
        self.assertContains(response, 'js/admin_crud.js?v=8')
        self.assertContains(response, 'js/recetas.js?v=3')
        self.assertContains(
            response,
            f'href="{reverse("perfil")}"',
        )
        self.assertContains(
            self.client.get(reverse('perfil')),
            f'href="{reverse("lista_recetas")}"',
        )

        response = self.client.post(
            reverse('lista_recetas'),
            self.datos_receta(),
        )
        self.assertRedirects(response, reverse('lista_recetas'))
        receta = Receta.objects.get(nombre='Masa básica')
        ingrediente = RecetaInsumo.objects.get(receta=receta)
        self.assertEqual(ingrediente.insumo, self.harina)
        self.assertEqual(ingrediente.medida_insumo, 'kg')
        self.assertEqual(ingrediente.cantidad_insumo, 0.5)

        datos = self.datos_receta(
            accion='editar_receta',
            receta_id=str(receta.pk),
            nombre='Masa actualizada',
            **{
                'ingredients-TOTAL_FORMS': '1',
                'ingredients-INITIAL_FORMS': '1',
                'ingredients-0-id': str(ingrediente.pk),
                'ingredients-0-receta': str(receta.pk),
                'ingredients-0-cantidad_insumo': '0.75',
            },
        )
        response = self.client.post(reverse('lista_recetas'), datos)
        self.assertRedirects(response, reverse('lista_recetas'))
        receta.refresh_from_db()
        ingrediente.refresh_from_db()
        self.assertEqual(receta.nombre, 'Masa actualizada')
        self.assertEqual(ingrediente.cantidad_insumo, 0.75)

        response = self.client.post(reverse('lista_recetas'), {
            'accion': 'eliminar_receta',
            'receta_id': str(receta.pk),
        })
        self.assertRedirects(response, reverse('lista_recetas'))
        self.assertFalse(Receta.objects.filter(pk=receta.pk).exists())
        self.assertFalse(RecetaInsumo.objects.filter(pk=ingrediente.pk).exists())

    def test_receta_rechaza_insumos_repetidos_y_unidades_incompatibles(self):
        response = self.client.post(
            reverse('lista_recetas'),
            self.datos_receta(**{
                'ingredients-TOTAL_FORMS': '2',
                'ingredients-1-insumo': str(self.harina.pk),
                'ingredients-1-cantidad_insumo': '1',
                'ingredients-1-medida_insumo': 'kg',
            }),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-open="crear"')
        self.assertContains(response, 'No repitas un insumo')
        self.assertFalse(Receta.objects.exists())

        response = self.client.post(
            reverse('lista_recetas'),
            self.datos_receta(**{
                'ingredients-0-medida_insumo': 'l',
            }),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-open="crear"')
        self.assertContains(response, 'La unidad debe ser compatible')
        self.assertEqual(
            response.context['formset'].forms[0].errors['medida_insumo'][0],
            'La unidad debe ser compatible con la unidad del insumo.',
        )
        self.assertEqual(
            response.context['form']['nombre'].value(),
            'Masa básica',
        )
        self.assertFalse(Receta.objects.exists())

    def test_error_al_editar_mantiene_abierto_el_formulario_y_los_datos(self):
        receta = Receta.objects.create(
            nombre='Receta original',
            descripcion='Descripción original',
        )
        fila = RecetaInsumo.objects.create(
            receta=receta,
            insumo=self.harina,
            cantidad_insumo=0.5,
            medida_insumo='kg',
        )
        datos = self.datos_receta(
            accion='editar_receta',
            receta_id=str(receta.pk),
            nombre='Nombre actualizado',
            **{
                'ingredients-TOTAL_FORMS': '1',
                'ingredients-INITIAL_FORMS': '1',
                'ingredients-0-id': str(fila.pk),
                'ingredients-0-receta': str(receta.pk),
                'ingredients-0-insumo': str(self.harina.pk),
                'ingredients-0-cantidad_insumo': '0.25',
                'ingredients-0-medida_insumo': 'l',
            },
        )

        response = self.client.post(reverse('lista_recetas'), datos)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-open="editar"')
        self.assertEqual(response.context['form']['nombre'].value(), 'Nombre actualizado')
        self.assertEqual(
            response.context['formset'].forms[0]['cantidad_insumo'].value(),
            '0.25',
        )
        receta.refresh_from_db()
        fila.refresh_from_db()
        self.assertEqual(receta.nombre, 'Receta original')
        self.assertEqual(fila.cantidad_insumo, 0.5)

    def test_unidades_disponibles_corresponden_a_la_dimension_del_insumo(self):
        response = self.client.get(reverse('lista_recetas'))

        unidades = response.context['unidades_por_insumo']
        self.assertEqual(unidades[str(self.harina.pk)]['unidades'], ['g', 'kg'])
        self.assertEqual(unidades[str(self.leche.pk)]['unidades'], ['ml', 'l'])
        self.assertEqual(unidades[str(self.harina.pk)]['unidad_inventario_label'], 'Kilogramo')

    def test_formulario_invalido_muestra_mensaje_para_alerta_administrativa(self):
        response = self.client.post(
            reverse('lista_recetas'),
            self.datos_receta(**{
                'ingredients-0-cantidad_insumo': '',
            }),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-open="crear"')
        self.assertContains(response, 'Este campo es obligatorio.')
        self.assertEqual(
            response.context['formset'].forms[0].errors['cantidad_insumo'][0],
            'Este campo es obligatorio.',
        )
        self.assertFalse(Receta.objects.exists())

    def test_creacion_exitosa_dispara_alerta_compartida(self):
        response = self.client.post(
            reverse('lista_recetas'),
            self.datos_receta(),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-tags="success"')
        self.assertContains(response, 'La receta')
        self.assertContains(response, 'js/admin_messages.js')

    def test_operaciones_muestra_limite_y_no_permite_preparar_sin_stock(self):
        receta = Receta.objects.create(nombre='Masa básica')
        RecetaInsumo.objects.create(
            receta=receta,
            insumo=self.harina,
            cantidad_insumo=0.5,
            medida_insumo='kg',
        )

        response = self.client.get(reverse('operaciones_recetas'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-recipe-max="0"')
        self.assertContains(response, 'Sin stock suficiente')
        self.assertContains(response, 'Volver al panel')
        self.assertContains(
            response,
            f'href="{reverse("perfil")}"',
        )
        self.assertContains(
            response,
            f'href="{reverse("lista_recetas")}"',
        )

        response = self.client.post(
            reverse('realizar_operacion_receta', args=[receta.pk]),
            {'veces': '1'},
        )
        self.assertRedirects(response, reverse('operaciones_recetas'))
        self.assertFalse(
            Movimiento.objects.filter(origen='RECETA').exists(),
        )

    def test_operacion_descuenta_solo_insumos_vinculados_y_valida_limite(self):
        receta = Receta.objects.create(nombre='Masa básica')
        RecetaInsumo.objects.create(
            receta=receta,
            insumo=self.harina,
            cantidad_insumo=500,
            medida_insumo='g',
        )
        self.registrar_stock(self.harina, '1.000', 'kg')
        self.registrar_stock(self.leche, '10.000', 'l')

        response = self.client.get(reverse('operaciones_recetas'))
        self.assertContains(response, 'data-recipe-max="2"')
        self.assertEqual(response.context['resumen_recetas'][0]['maximo'], 2)

        response = self.client.post(
            reverse('realizar_operacion_receta', args=[receta.pk]),
            {'veces': '3'},
        )
        self.assertRedirects(response, reverse('operaciones_recetas'))
        self.assertFalse(Movimiento.objects.filter(origen='RECETA').exists())

        response = self.client.post(
            reverse('realizar_operacion_receta', args=[receta.pk]),
            {'veces': '2'},
        )
        self.assertRedirects(response, reverse('operaciones_recetas'))
        salida = Movimiento.objects.get(origen='RECETA')
        self.assertEqual(salida.accion, 'SALIDA')
        self.assertEqual(salida.insumo, self.harina)
        self.assertEqual(salida.cantidad, 1)
        self.assertEqual(salida.unidad_medida, 'kg')
        self.assertFalse(
            Movimiento.objects.filter(origen='RECETA', insumo=self.leche).exists(),
        )

        response = self.client.get(reverse('operaciones_recetas'))
        self.assertContains(response, 'data-recipe-max="0"')

    def test_operacion_convierte_unidades_y_admite_cantidades_decimales(self):
        receta = Receta.objects.create(nombre='Bebida')
        RecetaInsumo.objects.create(
            receta=receta,
            insumo=self.leche,
            cantidad_insumo=250,
            medida_insumo='ml',
        )
        self.registrar_stock(self.leche, '1.000', 'l')

        response = self.client.post(
            reverse('realizar_operacion_receta', args=[receta.pk]),
            {'veces': '2'},
        )

        self.assertRedirects(response, reverse('operaciones_recetas'))
        salida = Movimiento.objects.get(origen='RECETA')
        self.assertEqual(salida.cantidad, 0.500)
        self.assertEqual(salida.unidad_medida, 'l')

    def test_operacion_rechaza_cantidad_invalida(self):
        receta = Receta.objects.create(nombre='Masa básica')
        RecetaInsumo.objects.create(
            receta=receta,
            insumo=self.harina,
            cantidad_insumo=0.5,
            medida_insumo='kg',
        )
        self.registrar_stock(self.harina, '2.000', 'kg')

        response = self.client.post(
            reverse('realizar_operacion_receta', args=[receta.pk]),
            {'veces': '0'},
        )

        self.assertRedirects(response, reverse('operaciones_recetas'))
        self.assertFalse(Movimiento.objects.filter(origen='RECETA').exists())

    def test_usuario_solo_lectura_no_ve_acciones_ni_puede_operar(self):
        receta = Receta.objects.create(nombre='Masa básica')
        RecetaInsumo.objects.create(
            receta=receta,
            insumo=self.harina,
            cantidad_insumo=0.5,
            medida_insumo='kg',
        )
        viewer = get_user_model().objects.create_user(
            username='viewer-recetas',
            password='Clave-segura-2026!',
            telefono='3009876543',
        )
        permiso_ver = Permission.objects.get(
            content_type__app_label='recetas',
            codename='view_receta',
        )
        viewer.user_permissions.add(permiso_ver)
        self.client.force_login(viewer)

        response = self.client.get(reverse('lista_recetas'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'data-open-crud-editor')
        self.assertNotContains(response, 'data-crud-delete-url')
        self.assertNotContains(response, '?editar=')

        response = self.client.get(reverse('operaciones_recetas'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="veces"')
        self.assertContains(response, 'Tu rol permite consultar el stock')

        response = self.client.post(
            reverse('realizar_operacion_receta', args=[receta.pk]),
            {'veces': '1'},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Movimiento.objects.filter(origen='RECETA').exists())
