from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from APP.usuarios.permissions import exigir_permiso
from .forms import ProveedorForm
from .models import Proveedor


def es_administrador(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def _get_posted_proveedor(value):
    value = str(value or '')
    if not value.isdecimal() or len(value) > 18:
        raise Http404
    return get_object_or_404(Proveedor, pk=int(value))


def _render_gestion(request, form=None, modal_open='', proveedor_actual=None):
    query = request.GET.get('q', '').strip()[:100]
    estado = request.GET.get('estado', 'activos')
    proveedores = Proveedor.objects.all()
    if estado == 'activos':
        proveedores = proveedores.filter(activo=True)
    elif estado == 'inactivos':
        proveedores = proveedores.filter(activo=False)
    else:
        estado = 'todos'
    if query:
        proveedores = proveedores.filter(
            Q(nombre__icontains=query)
            | Q(email__icontains=query)
            | Q(telefono__icontains=query)
            | Q(direccion__icontains=query)
        )
    proveedores = proveedores.order_by('-id')
    return render(request, 'gestion_proveedores.html', {
        'proveedores': proveedores,
        'form': form or ProveedorForm(instance=proveedor_actual),
        'proveedor_actual': proveedor_actual,
        'modo_edicion': proveedor_actual is not None,
        'modal_open': modal_open,
        'query': query,
        'estado': estado,
        'total_proveedores': Proveedor.objects.count(),
        'total_proveedores_activos': Proveedor.objects.filter(activo=True).count(),
        'total_proveedores_inactivos': Proveedor.objects.filter(activo=False).count(),
    })


@login_required(login_url='admin_login')
@user_passes_test(es_administrador, login_url='admin_login')
def gestion_proveedores(request):
    exigir_permiso(request, 'proveedores.view_proveedor')
    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'crear_proveedor':
            exigir_permiso(request, 'proveedores.add_proveedor')
            form = ProveedorForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Proveedor registrado exitosamente en PRISMA.')
                return redirect(request.path)
            return _render_gestion(request, form=form, modal_open='crear')

        if accion == 'editar_proveedor':
            exigir_permiso(request, 'proveedores.change_proveedor')
            proveedor = _get_posted_proveedor(request.POST.get('proveedor_id'))
            form = ProveedorForm(request.POST, instance=proveedor)
            if form.is_valid():
                proveedor = form.save()
                messages.success(
                    request,
                    f'Proveedor "{proveedor.nombre}" actualizado correctamente.',
                )
                return redirect(request.path)
            return _render_gestion(
                request,
                form=form,
                modal_open='editar',
                proveedor_actual=proveedor,
            )

        messages.error(request, 'No se reconoció la acción solicitada.')
    edit_id = request.GET.get('editar_proveedor', '')
    proveedor_actual = None
    if edit_id:
        if not edit_id.isdecimal() or len(edit_id) > 18:
            raise Http404
        proveedor_actual = get_object_or_404(Proveedor, pk=int(edit_id))
    return _render_gestion(
        request,
        modal_open='editar' if proveedor_actual else request.GET.get('modal', ''),
        proveedor_actual=proveedor_actual,
    )


@login_required(login_url='admin_login')
@user_passes_test(es_administrador, login_url='admin_login')
@require_GET
def detalle_proveedor(request, pk):
    exigir_permiso(request, 'proveedores.view_proveedor')
    proveedor = get_object_or_404(Proveedor, pk=pk)
    return JsonResponse({
        'id': proveedor.pk,
        'nombre': proveedor.nombre,
        'descripcion': proveedor.direccion or 'Sin dirección registrada.',
        'meta': [
            f'Teléfono: {proveedor.telefono}' if proveedor.telefono else 'Sin teléfono',
            f'Correo: {proveedor.email}' if proveedor.email else 'Sin correo',
        ],
        'imagen': '',
        'activo': proveedor.activo,
        'edit_url': f'{reverse("gestion_proveedores")}?editar_proveedor={proveedor.pk}',
        'status_url': reverse('cambiar_estado_proveedor', args=[proveedor.pk]),
    })


@login_required(login_url='admin_login')
@user_passes_test(es_administrador, login_url='admin_login')
@require_http_methods(['GET', 'POST'])
def editar_proveedor(request, pk):
    exigir_permiso(request, 'proveedores.view_proveedor')
    if request.method == 'POST':
        exigir_permiso(request, 'proveedores.change_proveedor')
    proveedor = get_object_or_404(Proveedor, pk=pk)
    if request.method == 'GET':
        return redirect(f'{reverse("gestion_proveedores")}?editar_proveedor={proveedor.pk}')
    form = ProveedorForm(request.POST, instance=proveedor)
    if form.is_valid():
        proveedor = form.save()
        messages.success(request, f'Proveedor "{proveedor.nombre}" actualizado correctamente.')
        return redirect('gestion_proveedores')
    return _render_gestion(
        request,
        form=form,
        modal_open='editar',
        proveedor_actual=proveedor,
    )


@login_required(login_url='admin_login')
@user_passes_test(es_administrador, login_url='admin_login')
@require_POST
def cambiar_estado_proveedor(request, pk):
    exigir_permiso(request, 'proveedores.change_proveedor')
    proveedor = get_object_or_404(Proveedor, pk=pk)
    valor = request.POST.get('activo')
    if valor not in ('true', 'false'):
        return JsonResponse(
            {'error': 'Selecciona si el proveedor está activo.'},
            status=400,
        )
    proveedor.activo = valor == 'true'
    proveedor.save(update_fields=['activo'])
    return JsonResponse({
        'id': proveedor.pk,
        'activo': proveedor.activo,
        'message': (
            'Proveedor activado correctamente.'
            if proveedor.activo else 'Proveedor desactivado correctamente.'
        ),
    })


@login_required(login_url='admin_login')
@user_passes_test(es_administrador, login_url='admin_login')
@require_POST
def eliminar_proveedor(request, pk):
    exigir_permiso(request, 'proveedores.delete_proveedor')
    proveedor = get_object_or_404(Proveedor, pk=pk)
    nombre_proveedor = proveedor.nombre
    proveedor.delete()
    messages.success(request, f'El proveedor "{nombre_proveedor}" ha sido eliminado del sistema.')
    return redirect('gestion_proveedores')
