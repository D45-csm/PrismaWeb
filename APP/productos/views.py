from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST, require_http_methods

from APP.usuarios.permissions import exigir_permiso
from .forms import ProductoForm
from .models import CategoriaProducto, Producto, DEFAULT_PRODUCT_IMAGE


def es_administrador(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def _nombres_imagenes(producto):
    nombres = set()
    for field_name in (
        'imagen_principal',
        'imagen_2',
        'imagen_3',
        'imagen_4',
    ):
        image = getattr(producto, field_name)
        if image:
            nombres.add(image.name)
    return nombres


def _eliminar_imagenes_reemplazadas(producto, nombres_anteriores):
    nombres_actuales = _nombres_imagenes(producto)
    for nombre in nombres_anteriores - nombres_actuales:
        if nombre != DEFAULT_PRODUCT_IMAGE:
            producto.imagen_principal.storage.delete(nombre)

# 1. GESTIÓN Y LISTADO DE PRODUCTOS
def _render_admin_gestion(request, form=None, editor_mode='', producto_editar=None):
    categorias = CategoriaProducto.objects.annotate(
        total_productos=Count('producto'),
    ).order_by('nombre')
    query = request.GET.get('q', '').strip()[:100]
    estado = request.GET.get('estado', 'activos')
    categoria_id = request.GET.get('categoria', '')
    productos = Producto.objects.select_related('categoria')
    if estado == 'activos':
        productos = productos.filter(activo=True)
    elif estado == 'inactivos':
        productos = productos.filter(activo=False)
    else:
        estado = 'todos'

    if categoria_id.isdecimal() and len(categoria_id) <= 18:
        productos = productos.filter(categoria_id=int(categoria_id))
    else:
        categoria_id = ''
    if query:
        productos = productos.filter(
            Q(nombre__icontains=query)
            | Q(categoria__nombre__icontains=query)
            | Q(descripcion__icontains=query)
        )

    return render(request, 'productos/gestion_productos.html', {
        'productos': productos.order_by('-id'),
        'categorias': categorias,
        'categoria_seleccionada': categoria_id,
        'query': query,
        'estado': estado,
        'total_productos': Producto.objects.count(),
        'total_productos_activos': Producto.objects.filter(activo=True).count(),
        'total_productos_inactivos': Producto.objects.filter(activo=False).count(),
        'form': form or ProductoForm(instance=producto_editar),
        'producto_editar': producto_editar,
        'editor_mode': editor_mode,
    })


def gestion_productos(request):

    if es_administrador(request.user):
        exigir_permiso(request, 'productos.view_producto')
        return _render_admin_gestion(request)

    else:
        productos = Producto.objects.filter(activo=True).order_by('-id')
        template = 'productos/lista_productos.html'

    return render(request, template, {
        'productos': productos
    })


# 2. CREAR PRODUCTO
@login_required(login_url='admin_login')
@user_passes_test(es_administrador, login_url='admin_login')
@require_http_methods(['GET', 'POST'])
def crear_producto(request):
    exigir_permiso(request, 'productos.view_producto')
    exigir_permiso(request, 'productos.add_producto')
    form = ProductoForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        producto = form.save(commit=False)
        if not producto.imagen_principal:
            producto.imagen_principal = DEFAULT_PRODUCT_IMAGE
        producto.activo = True
        producto.save()
        messages.success(request, 'Producto creado correctamente.')
        return redirect('lista_productos')

    if request.method == 'POST':
        messages.error(request, 'Revisa los campos marcados para corregir el formulario.')
    return _render_admin_gestion(request, form=form, editor_mode='crear')


# 3. EDITAR PRODUCTO
@login_required(login_url='admin_login')
@user_passes_test(es_administrador, login_url='admin_login')
@require_http_methods(['GET', 'POST'])
def editar_producto(request, id):
    exigir_permiso(request, 'productos.view_producto')
    exigir_permiso(request, 'productos.change_producto')
    producto = get_object_or_404(Producto, id=id)
    form = ProductoForm(
        request.POST or None,
        request.FILES or None,
        instance=producto,
    )
    if request.method == 'POST' and form.is_valid():
        nombres_anteriores = _nombres_imagenes(producto)
        producto = form.save(commit=False)
        for field_name in (
            'imagen_principal',
            'imagen_2',
            'imagen_3',
            'imagen_4',
        ):
            if (
                form.cleaned_data[f'eliminar_{field_name}']
                and not request.FILES.get(field_name)
            ):
                setattr(producto, field_name, None)
        producto.save()
        _eliminar_imagenes_reemplazadas(producto, nombres_anteriores)
        messages.success(request, 'Producto actualizado correctamente.')
        return redirect('lista_productos')

    if request.method == 'POST':
        messages.error(request, 'Revisa los campos marcados para corregir el formulario.')
    return _render_admin_gestion(
        request,
        form=form,
        editor_mode='editar',
        producto_editar=producto,
    )


@login_required(login_url='admin_login')
@user_passes_test(es_administrador, login_url='admin_login')
@require_http_methods(['GET', 'POST'])
def detalle_producto(request, id):
    exigir_permiso(
        request,
        'productos.change_producto' if request.method == 'POST'
        else 'productos.view_producto',
    )
    producto = get_object_or_404(Producto.objects.select_related('categoria'), pk=id)
    if request.method == 'POST':
        activo = request.POST.get('activo')
        if activo not in ('true', 'false'):
            return JsonResponse({'error': 'Selecciona el estado del producto.'}, status=400)
        producto.activo = activo == 'true'
        producto.save(update_fields=['activo'])
        return JsonResponse({
            'id': producto.pk,
            'activo': producto.activo,
            'message': (
                'Producto activado correctamente.'
                if producto.activo else 'Producto desactivado correctamente.'
            ),
        })

    return JsonResponse({
        'id': producto.pk,
        'nombre': producto.nombre,
        'descripcion': producto.descripcion,
        'meta': [producto.categoria.nombre, f'${producto.precio}'],
        'imagen': producto.imagen_principal.url if producto.imagen_principal else '',
        'activo': producto.activo,
        'edit_url': reverse('editar_producto', args=[producto.pk]),
        'status_url': reverse('detalle_producto', args=[producto.pk]),
    })


# 4. ELIMINAR PRODUCTO
@login_required(login_url='admin_login')
@user_passes_test(es_administrador, login_url='admin_login')
@require_POST
def eliminar_producto(request, id):
    exigir_permiso(request, 'productos.delete_producto')
    producto = get_object_or_404(Producto, id=id)
    nombres_imagenes = _nombres_imagenes(producto)
    producto.delete()
    for nombre in nombres_imagenes:
        if nombre != DEFAULT_PRODUCT_IMAGE:
            producto.imagen_principal.storage.delete(nombre)
    messages.success(request, 'Producto eliminado correctamente.')
    return redirect('lista_productos')
