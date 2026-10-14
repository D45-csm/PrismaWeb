from django.db.models import Count, Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

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
    insumo = get_object_or_404(Insumo.objects.select_related('categoria'), pk=pk)

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
            'unidad_medida': insumo.unidad_medida,
            'unidad_medida_display': insumo.get_unidad_medida_display(),
            'imagen': insumo.imagen.url if insumo.imagen else '',
            'activo': insumo.activo,
            'message': 'Insumo actualizado correctamente.',
        })

    if accion in ('eliminar_insumo', 'restaurar_insumo'):
        insumo.activo = accion == 'restaurar_insumo'
        insumo.save(update_fields=['activo'])
        return JsonResponse({
            'id': insumo.pk,
            'activo': insumo.activo,
            'message': (
                'Insumo restaurado correctamente.'
                if insumo.activo else
                'Insumo eliminado del inventario. Su historial se conservó.'
            ),
        })

    return JsonResponse({'error': 'La acción solicitada no es válida.'}, status=400)


def _render_gestion(request, categoria_form=None, insumo_form=None):
    categorias = CategoriaInsumo.objects.annotate(
        total_insumos=Count('insumo'),
    ).order_by('nombre')
    total_categorias = categorias.count()
    categoria_id = (
        request.POST.get('categoria')
        or request.POST.get('categoria_id')
        or request.GET.get('categoria')
    )
    categoria_seleccionada = categorias.filter(pk=categoria_id).first() if categoria_id else None
    categoria_busqueda = request.GET.get('categoria_q', '').strip()[:100]
    categorias_visibles = (
        categorias.filter(nombre__icontains=categoria_busqueda)
        if categoria_busqueda else categorias
    )
    query = request.GET.get('q', '').strip()[:100]
    estado = request.GET.get('estado', 'activos')
    insumos = Insumo.objects.select_related('categoria')

    if estado == 'activos':
        insumos = insumos.filter(activo=True)
    elif estado == 'inactivos':
        insumos = insumos.filter(activo=False)
    else:
        estado = 'todos'

    if categoria_seleccionada:
        insumos = insumos.filter(categoria=categoria_seleccionada)
    if query:
        insumos = insumos.filter(
            Q(nombre__icontains=query) | Q(descripcion__icontains=query),
        )
    insumos = insumos.order_by('nombre')
    return render(request, 'insumos/gestion_categorias.html', {
        'categorias': categorias_visibles,
        'total_categorias': total_categorias,
        'categoria_seleccionada': categoria_seleccionada,
        'categoria_busqueda': categoria_busqueda,
        'categoria_form': (
            categoria_form
            if categoria_form and not categoria_form.instance.pk
            else CategoriaInsumoForm()
        ),
        'editar_categoria_form': (
            categoria_form
            if (
                categoria_form
                and categoria_seleccionada
                and categoria_form.instance.pk == categoria_seleccionada.pk
            )
            else (
                CategoriaInsumoForm(
                    instance=categoria_seleccionada,
                    prefix=f'categoria-{categoria_seleccionada.pk}',
                )
                if categoria_seleccionada else None
            )
        ),
        'insumo_form': insumo_form or InsumoForm(
            initial=(
                {'categoria': categoria_seleccionada.pk}
                if categoria_seleccionada else None
            ),
        ),
        'insumos': insumos,
        'query': query,
        'estado': estado,
        'total_insumos': Insumo.objects.filter(activo=True).count(),
    })


@login_required(login_url='admin_login')
@user_passes_test(es_administrador, login_url='admin_login')
def gestion_categorias(request):
    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'crear_categoria':
            form = CategoriaInsumoForm(request.POST)
            if form.is_valid():
                categoria = form.save()
                messages.success(
                    request,
                    'Categoría creada correctamente.',
                    extra_tags='insumos',
                )
                return redirect(f'{request.path}?categoria={categoria.pk}')
            return _render_gestion(request, categoria_form=form)

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
                messages.success(
                    request,
                    'Categoría actualizada correctamente.',
                    extra_tags='insumos',
                )
                return redirect(f'{request.path}?categoria={categoria.pk}')
            return _render_gestion(request, categoria_form=form)

        if accion == 'eliminar_categoria':
            categoria = _get_posted_object(
                CategoriaInsumo,
                request.POST.get('categoria_id'),
            )
            if Insumo.objects.filter(categoria=categoria).exists():
                messages.error(
                    request,
                    'No puedes eliminar una categoría que todavía tiene insumos. '
                    'Mueve o elimina sus insumos primero.',
                    extra_tags='insumos',
                )
                return redirect(request.path)
            categoria.delete()
            messages.success(
                request,
                'Categoría eliminada correctamente.',
                extra_tags='insumos',
            )
            return redirect(request.path)

        if accion == 'crear_insumo':
            form = InsumoForm(request.POST, request.FILES)
            if form.is_valid():
                insumo = form.save()
                messages.success(
                    request,
                    'Insumo agregado a la categoría.',
                    extra_tags='insumos',
                )
                return redirect(f'{request.path}?categoria={insumo.categoria_id}')
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
                insumo = form.save()
                messages.success(
                    request,
                    'Insumo actualizado correctamente.',
                    extra_tags='insumos',
                )
                return redirect(f'{request.path}?categoria={insumo.categoria_id}')
            return _render_gestion(request, insumo_form=form)

        if accion in ('eliminar_insumo', 'restaurar_insumo'):
            insumo = _get_posted_object(
                Insumo,
                request.POST.get('insumo_id'),
            )
            insumo.activo = accion == 'restaurar_insumo'
            insumo.save(update_fields=['activo'])
            messages.success(
                request,
                'Insumo restaurado correctamente.'
                if insumo.activo else
                'Insumo desactivado. Su historial se conservó.',
                extra_tags='insumos',
            )
            return redirect(f'{request.path}?categoria={insumo.categoria_id}')

        messages.error(
            request,
            'No se reconoció la acción solicitada.',
            extra_tags='insumos',
        )

    return _render_gestion(request)
