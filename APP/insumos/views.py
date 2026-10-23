from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count
from django.db.models.deletion import ProtectedError
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from APP.usuarios.permissions import exigir_permiso
from APP.proveedores.models import Proveedor

from .forms import CategoriaInsumoForm, InsumoForm
from .models import CategoriaInsumo, Insumo


def es_administrador(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def _get_posted_object(model, value):
    if not str(value or '').isdecimal():
        raise Http404
    return get_object_or_404(model, pk=int(value))


@login_required(login_url='admin_login')
@user_passes_test(es_administrador, login_url='admin_login')
@require_http_methods(['GET', 'POST'])
def detalle_insumo(request, pk):
    exigir_permiso(
        request,
        'insumos.view_insumo' if request.method == 'GET'
        else _permiso_accion_insumo(request.POST.get('accion')),
    )
    insumo = get_object_or_404(
        Insumo.objects.select_related('categoria', 'proveedor_referencia'),
        pk=pk,
    )

    if request.method == 'GET':
        return JsonResponse({
            'id': insumo.pk,
            'nombre': insumo.nombre,
            'descripcion': insumo.descripcion or '',
            'categoria': insumo.categoria.nombre,
            'categoria_id': insumo.categoria_id,
            'categorias': list(
                CategoriaInsumo.objects.order_by('nombre').values('id', 'nombre')
            ),
            'proveedor_referencia': (
                insumo.proveedor_referencia.nombre
                if insumo.proveedor_referencia else ''
            ),
            'proveedor_referencia_id': insumo.proveedor_referencia_id,
            'proveedores': list(
                Proveedor.objects.order_by('nombre').values('id', 'nombre')
            ),
            'unidad_medida': insumo.unidad_medida,
            'unidad_medida_display': insumo.get_unidad_medida_display(),
            'unidades': [
                {'id': value, 'nombre': label}
                for value, label in Insumo.unidad_medida_choices
            ],
            'imagen': insumo.imagen.url if insumo.imagen else '',
            'activo': insumo.activo,
        })

    accion = request.POST.get('accion')
    if accion == 'eliminar_insumo':
        try:
            insumo.delete()
        except ProtectedError:
            return JsonResponse(
                {
                    'error': (
                        'No se puede eliminar este insumo porque tiene movimientos '
                        'de inventario o compras asociados. Puedes marcarlo como '
                        'no disponible.'
                    ),
                },
                status=409,
            )
        return JsonResponse({
            'id': pk,
            'deleted': True,
            'message': 'Insumo eliminado correctamente.',
        })

    if accion == 'editar_insumo':
        form = InsumoForm(
            request.POST,
            request.FILES,
            instance=insumo,
            prefix=f'insumo-{insumo.pk}',
        )
        if not form.is_valid():
            return JsonResponse(
                {'errors': form.errors.get_json_data()},
                status=400,
            )

        insumo = form.save()
        return JsonResponse({
            'id': insumo.pk,
            'nombre': insumo.nombre,
            'descripcion': insumo.descripcion or '',
            'categoria': insumo.categoria.nombre,
            'categoria_id': insumo.categoria_id,
            'proveedor_referencia': (
                insumo.proveedor_referencia.nombre
                if insumo.proveedor_referencia else ''
            ),
            'proveedor_referencia_id': insumo.proveedor_referencia_id,
            'unidad_medida': insumo.unidad_medida,
            'unidad_medida_display': insumo.get_unidad_medida_display(),
            'imagen': insumo.imagen.url if insumo.imagen else '',
            'activo': insumo.activo,
            'message': 'Insumo actualizado correctamente.',
        })

    if accion == 'cambiar_disponibilidad':
        valor = request.POST.get('activo')
        if valor not in ('true', 'false'):
            return JsonResponse(
                {'error': 'Selecciona si el insumo está disponible.'},
                status=400,
            )
        insumo.activo = valor == 'true'
        insumo.save(update_fields=['activo'])
        return JsonResponse({
            'id': insumo.pk,
            'activo': insumo.activo,
            'message': (
                'Insumo activado correctamente.'
                if insumo.activo else 'Insumo desactivado correctamente.'
            ),
        })

    return JsonResponse({'error': 'La acción solicitada no es válida.'}, status=400)


def _render_gestion(
    request,
    categoria_form=None,
    editar_categoria_form=None,
    insumo_form=None,
    categoria_modal='',
):
    categorias = CategoriaInsumo.objects.annotate(
        total_insumos=Count('insumo'),
    ).order_by('nombre')
    total_categorias = categorias.count()
    categoria_id = (
        request.POST.get('categoria_id')
        if request.method == 'POST'
        else request.GET.get('editar_categoria')
    )
    categoria_seleccionada = None
    if str(categoria_id or '').isdecimal():
        categoria_seleccionada = categorias.filter(pk=int(categoria_id)).first()
    categoria_busqueda = request.GET.get('categoria_q', '').strip()[:100]
    categorias_visibles = (
        categorias.filter(nombre__icontains=categoria_busqueda)
        if categoria_busqueda else categorias
    )
    query = request.GET.get('q', '').strip()[:100]
    campo = request.GET.get('campo', 'nombre')
    if campo not in ('nombre', 'categoria', 'tamano'):
        campo = 'nombre'
    estado = request.GET.get('estado', 'activos')
    insumos = Insumo.objects.select_related('categoria', 'proveedor_referencia')

    if estado == 'activos':
        insumos = insumos.filter(activo=True)
    elif estado == 'inactivos':
        insumos = insumos.filter(activo=False)
    else:
        estado = 'todos'

    if query:
        if campo == 'categoria':
            insumos = insumos.filter(categoria__nombre__icontains=query)
        elif campo == 'tamano':
            unidades = [
                value
                for value, label in Insumo.unidad_medida_choices
                if query.casefold() in value.casefold()
                or query.casefold() in label.casefold()
            ]
            insumos = insumos.filter(unidad_medida__in=unidades)
        else:
            insumos = insumos.filter(nombre__icontains=query)
    insumos = insumos.order_by('nombre')
    return render(request, 'insumos/gestion_categorias.html', {
        'categorias': categorias_visibles,
        'total_categorias': total_categorias,
        'categoria_seleccionada': categoria_seleccionada,
        'categoria_busqueda': categoria_busqueda,
        'categoria_form': categoria_form or CategoriaInsumoForm(),
        'editar_categoria_form': editar_categoria_form or (
            CategoriaInsumoForm(
                instance=categoria_seleccionada,
                prefix=f'categoria-{categoria_seleccionada.pk}',
            )
            if categoria_seleccionada else None
        ),
        'categoria_modal': categoria_modal or (
            'editar' if categoria_seleccionada else ''
        ),
        'insumo_form': insumo_form or InsumoForm(),
        'insumos': insumos,
        'query': query,
        'campo': campo,
        'estado': estado,
        'mostrar_resultados': bool(query or estado != 'activos'),
        'total_insumos': Insumo.objects.filter(activo=True).count(),
    })


def _permiso_accion_insumo(accion):
    permisos = {
        'eliminar_insumo': 'insumos.delete_insumo',
        'editar_insumo': 'insumos.change_insumo',
        'cambiar_disponibilidad': 'insumos.change_insumo',
    }
    return permisos.get(accion, 'insumos.view_insumo')


@login_required(login_url='admin_login')
@user_passes_test(es_administrador, login_url='admin_login')
def gestion_categorias(request):
    exigir_permiso(request, 'insumos.view_insumo')
    if request.method == 'POST':
        accion = request.POST.get('accion')
        permisos = {
            'crear_categoria': 'insumos.add_categoriainsumo',
            'editar_categoria': 'insumos.change_categoriainsumo',
            'eliminar_categoria': 'insumos.delete_categoriainsumo',
            'crear_insumo': 'insumos.add_insumo',
            'editar_insumo': 'insumos.change_insumo',
        }
        exigir_permiso(
            request,
            permisos.get(accion, 'insumos.view_insumo'),
        )

        if accion == 'crear_categoria':
            form = CategoriaInsumoForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Categoría creada correctamente.')
                return redirect(request.path)
            return _render_gestion(
                request,
                categoria_form=form,
                categoria_modal='crear',
            )

        if accion == 'editar_categoria':
            categoria = _get_posted_object(
                CategoriaInsumo,
                request.POST.get('categoria_id'),
            )
            form = CategoriaInsumoForm(
                request.POST,
                instance=categoria,
                prefix=f'categoria-{categoria.pk}',
            )
            if form.is_valid():
                form.save()
                messages.success(request, 'Categoría actualizada correctamente.')
                return redirect(request.path)
            return _render_gestion(
                request,
                editar_categoria_form=form,
                categoria_modal='editar',
            )

        if accion == 'eliminar_categoria':
            categoria = _get_posted_object(
                CategoriaInsumo,
                request.POST.get('categoria_id'),
            )
            if Insumo.objects.filter(categoria=categoria).exists():
                messages.error(
                    request,
                    'No puedes eliminar una categoría que todavía tiene insumos. '
                    'Reasigna o desactiva sus insumos primero.',
                )
                return redirect(request.path)
            categoria.delete()
            messages.success(
                request,
                'Categoría eliminada correctamente.',
            )
            return redirect(request.path)

        if accion == 'crear_insumo':
            form = InsumoForm(request.POST, request.FILES)
            if form.is_valid():
                insumo = form.save()
                messages.success(request, 'Insumo agregado correctamente.')
                query = urlencode({'q': insumo.nombre, 'campo': 'nombre'})
                return redirect(f'{request.path}?{query}')
            return _render_gestion(request, insumo_form=form)

        if accion == 'editar_insumo':
            insumo = _get_posted_object(
                Insumo,
                request.POST.get('insumo_id'),
            )
            form = InsumoForm(
                request.POST,
                request.FILES,
                instance=insumo,
                prefix=f'insumo-{insumo.pk}',
            )
            if form.is_valid():
                form.save()
                messages.success(request, 'Insumo actualizado correctamente.')
                return redirect(request.path)
            return _render_gestion(request, insumo_form=form)

        messages.error(request, 'No se reconoció la acción solicitada.')

    return _render_gestion(request)
