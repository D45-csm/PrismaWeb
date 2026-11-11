from decimal import InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from APP.inventario.models import Movimiento
from APP.insumos.models import Insumo
from APP.usuarios.permissions import (
    exigir_permiso,
    usuario_puede_acceder,
    usuario_puede_entrar_panel,
)

from .forms import RecetaForm, RecetaInsumoFormSet
from .models import Receta
from .services import (
    cantidad_para_movimiento,
    cantidades_en_base,
    maximo_para_insumo,
    resumen_recetas,
    unidades_compatibles,
)


def es_administrador(user):
    return usuario_puede_entrar_panel(user)


def _render_gestion(
    request,
    form=None,
    formset=None,
    receta_editar=None,
    editor_mode=None,
):
    query = request.GET.get('q', '').strip()[:100]
    estado = request.GET.get('estado', 'todos')
    recetas = Receta.objects.annotate(
        total_insumos=Count('recetainsumo'),
    )
    if estado == 'activos':
        recetas = recetas.filter(activo=True)
    elif estado == 'inactivos':
        recetas = recetas.filter(activo=False)
    else:
        estado = 'todos'
    if query:
        recetas = recetas.filter(nombre__icontains=query)

    etiquetas_unidad = dict(Insumo.unidad_medida_choices)
    unidades_por_insumo = {
        str(insumo_id): {
            'unidades': unidades_compatibles(unidad),
            'unidad_inventario': unidad,
            'unidad_inventario_label': etiquetas_unidad.get(unidad, unidad),
        }
        for insumo_id, unidad in Insumo.objects.values_list(
            'pk',
            'unidad_medida',
        )
    }

    return render(request, 'recetas/gestion_recetas.html', {
        'recetas': recetas.order_by('nombre'),
        'query': query,
        'estado': estado,
        'total_recetas': Receta.objects.count(),
        'total_recetas_activas': Receta.objects.filter(activo=True).count(),
        'form': form or RecetaForm(instance=receta_editar),
        'formset': formset or RecetaInsumoFormSet(
            instance=receta_editar or Receta(),
            prefix='ingredients',
        ),
        'receta_editar': receta_editar,
        'editor_mode': editor_mode or ('editar' if receta_editar else ''),
        'unidades_por_insumo': unidades_por_insumo,
        'puede_agregar': usuario_puede_acceder(
            request.user,
            'recetas.add_receta',
        ),
        'puede_cambiar': usuario_puede_acceder(
            request.user,
            'recetas.change_receta',
        ),
        'puede_eliminar': usuario_puede_acceder(
            request.user,
            'recetas.delete_receta',
        ),
        'puede_operar': usuario_puede_acceder(
            request.user,
            'recetas.change_receta',
        ),
    })


@login_required(login_url='login')
@user_passes_test(es_administrador, login_url='login')
@require_http_methods(['GET', 'POST'])
def gestion_recetas(request):
    if request.method == 'GET':
        exigir_permiso(request, 'recetas.view_receta')
        receta_editar = None
        receta_id = request.GET.get('editar', '')
        if receta_id:
            if not receta_id.isdecimal() or len(receta_id) > 18:
                raise Http404
            exigir_permiso(request, 'recetas.change_receta')
            receta_editar = get_object_or_404(Receta, pk=int(receta_id))
        return _render_gestion(request, receta_editar=receta_editar)

    accion = request.POST.get('accion')
    permisos = {
        'crear_receta': 'recetas.add_receta',
        'editar_receta': 'recetas.change_receta',
        'eliminar_receta': 'recetas.delete_receta',
    }
    if accion not in permisos:
        messages.error(request, 'La acción solicitada no es válida.')
        return redirect('lista_recetas')
    exigir_permiso(request, permisos[accion])

    if accion == 'eliminar_receta':
        receta_id = request.POST.get('receta_id', '')
        if not receta_id.isdecimal() or len(receta_id) > 18:
            raise Http404
        receta = get_object_or_404(Receta, pk=int(receta_id))
        nombre = receta.nombre
        receta.delete()
        messages.success(request, f'La receta "{nombre}" fue eliminada.')
        return redirect('lista_recetas')

    receta_editar = None
    if accion == 'editar_receta':
        receta_id = request.POST.get('receta_id', '')
        if not receta_id.isdecimal() or len(receta_id) > 18:
            raise Http404
        receta_editar = get_object_or_404(Receta, pk=int(receta_id))

    form = RecetaForm(request.POST, instance=receta_editar)
    formset = RecetaInsumoFormSet(
        request.POST,
        instance=receta_editar or Receta(),
        prefix='ingredients',
    )
    form_valido = form.is_valid()
    formset_valido = formset.is_valid()
    if form_valido and formset_valido:
        with transaction.atomic():
            receta = form.save()
            formset.instance = receta
            formset.save()
        messages.success(
            request,
            f'La receta "{receta.nombre}" fue '
            f'{"actualizada" if accion == "editar_receta" else "creada"} correctamente.',
        )
        return redirect('lista_recetas')

    for ingredient_form in formset.forms:
        for field_name in ingredient_form.errors:
            if field_name in ingredient_form.fields:
                ingredient_form.fields[field_name].widget.attrs['aria-invalid'] = 'true'

    return _render_gestion(
        request,
        form=form,
        formset=formset,
        receta_editar=receta_editar,
        editor_mode='editar' if receta_editar else 'crear',
    )


@login_required(login_url='login')
@user_passes_test(es_administrador, login_url='login')
@require_http_methods(['GET'])
def operaciones_recetas(request):
    exigir_permiso(request, 'recetas.view_receta')
    recetas = list(
        Receta.objects.filter(activo=True)
        .prefetch_related('recetainsumo_set__insumo')
        .order_by('nombre'),
    )
    resumen, _ = resumen_recetas(recetas)
    return render(request, 'recetas/operaciones_recetas.html', {
        'resumen_recetas': resumen,
        'puede_operar': usuario_puede_acceder(
            request.user,
            'recetas.change_receta',
        ),
    })


@login_required(login_url='login')
@user_passes_test(es_administrador, login_url='login')
@require_http_methods(['POST'])
def realizar_operacion_receta(request, pk):
    exigir_permiso(request, 'recetas.change_receta')
    try:
        veces = int(request.POST.get('veces', ''))
    except (TypeError, ValueError):
        messages.error(request, 'Indica una cantidad válida de preparaciones.')
        return redirect('operaciones_recetas')
    if veces < 1:
        messages.error(request, 'La cantidad debe ser un número entero mayor que cero.')
        return redirect('operaciones_recetas')

    with transaction.atomic():
        receta = get_object_or_404(
            Receta.objects.select_for_update(),
            pk=pk,
            activo=True,
        )
        filas = list(
            receta.recetainsumo_set.select_related('insumo').order_by('insumo_id'),
        )
        if not filas:
            messages.error(request, 'Esta receta no tiene insumos vinculados.')
            return redirect('operaciones_recetas')

        insumo_ids = [fila.insumo_id for fila in filas]
        list(
            # Serializa las operaciones de una misma materia prima en motores
            # que implementan SELECT FOR UPDATE.
            receta.insumos.select_for_update().filter(
                pk__in=insumo_ids,
            ).order_by('pk'),
        )
        stocks = cantidades_en_base(insumo_ids)
        limites = [maximo_para_insumo(fila, stocks) for fila in filas]
        maximo = min(limites) if limites else 0
        if maximo == 0:
            messages.error(
                request,
                'No se puede preparar esta receta: no hay stock suficiente '
                'para una preparación.',
            )
            return redirect('operaciones_recetas')
        if veces > maximo:
            messages.error(
                request,
                f'Solo puedes realizar {maximo} preparación(es) con el stock actual.',
            )
            return redirect('operaciones_recetas')

        try:
            movimientos = [
                Movimiento(
                    origen='RECETA',
                    accion='SALIDA',
                    usuario=request.user,
                    insumo=fila.insumo,
                    cantidad=cantidad_para_movimiento(fila, veces),
                    unidad_medida=fila.insumo.unidad_medida,
                )
                for fila in filas
            ]
        except (ValueError, InvalidOperation) as error:
            messages.error(request, str(error))
            return redirect('operaciones_recetas')
        Movimiento.objects.bulk_create(movimientos)

    messages.success(
        request,
        f'Se realizaron {veces} preparación(es) de "{receta.nombre}" y '
        'se descontaron sus insumos del inventario.',
    )
    return redirect('operaciones_recetas')
