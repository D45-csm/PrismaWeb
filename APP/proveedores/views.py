from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.urls import reverse

from .forms import ProveedorForm
from .models import Proveedor


def es_administrador(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def _get_proveedor(value):
    if not str(value or '').isdecimal():
        raise Http404
    return get_object_or_404(Proveedor, pk=int(value))


@login_required(login_url='admin_login')
@user_passes_test(es_administrador, login_url='admin_login')
def gestion_proveedores(request):
    proveedor_id = request.GET.get('proveedor')
    proveedor_seleccionado = (
        get_object_or_404(Proveedor, pk=proveedor_id)
        if proveedor_id and str(proveedor_id).isdecimal()
        else None
    )
    return render(request, 'proveedores/gestion_proveedores.html', {
        'proveedores': Proveedor.objects.order_by('nombre'),
        'proveedor_seleccionado': proveedor_seleccionado,
        'proveedor_form': (
            ProveedorForm(
                instance=proveedor_seleccionado,
                prefix=f'proveedor-{proveedor_seleccionado.pk}',
            )
            if proveedor_seleccionado else ProveedorForm()
        ),
    })


@login_required(login_url='admin_login')
@user_passes_test(es_administrador, login_url='admin_login')
@require_POST
def guardar_proveedor(request):
    accion = request.POST.get('accion')
    if accion == 'crear':
        proveedor = None
    elif accion == 'editar':
        proveedor = _get_proveedor(request.POST.get('proveedor_id'))
    else:
        messages.error(request, 'La acción solicitada no es válida.')
        return redirect('gestion_proveedores')

    form = ProveedorForm(
        request.POST,
        instance=proveedor,
        prefix=f'proveedor-{proveedor.pk}' if proveedor else None,
    )
    if form.is_valid():
        proveedor = form.save()
        messages.success(
            request,
            'Proveedor creado correctamente.'
            if accion == 'crear'
            else 'Proveedor actualizado correctamente.',
        )
        return redirect(f'{reverse("gestion_proveedores")}?proveedor={proveedor.pk}')
    messages.error(request, 'Revisa los datos del formulario de proveedor.')
    return render(request, 'proveedores/gestion_proveedores.html', {
        'proveedores': Proveedor.objects.order_by('nombre'),
        'proveedor_seleccionado': form.instance if form.instance.pk else None,
        'proveedor_form': form,
    }, status=400)


@login_required(login_url='admin_login')
@user_passes_test(es_administrador, login_url='admin_login')
@require_POST
def cambiar_estado_proveedor(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    proveedor.activo = not proveedor.activo
    proveedor.save(update_fields=['activo'])
    messages.success(
        request,
        'Proveedor activado correctamente.'
        if proveedor.activo
        else 'Proveedor desactivado; los insumos vinculados conservarán su referencia.',
    )
    return redirect('gestion_proveedores')
