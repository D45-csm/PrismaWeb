from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST, require_http_methods

from .forms import ProductoForm
from .models import Producto, DEFAULT_PRODUCT_IMAGE


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
def gestion_productos(request):

    if es_administrador(request.user):
        productos = Producto.objects.all().order_by('-id')
        template = 'productos/gestion_productos.html'

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
    form = ProductoForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        producto = form.save(commit=False)
        if not producto.imagen_principal:
            producto.imagen_principal = DEFAULT_PRODUCT_IMAGE
        producto.activo = True
        producto.save()
        messages.success(request, 'Producto creado correctamente.')
        return redirect('lista_productos')

    return render(request, 'productos/crear_producto.html', {'form': form})


# 3. EDITAR PRODUCTO
@login_required(login_url='admin_login')
@user_passes_test(es_administrador, login_url='admin_login')
@require_http_methods(['GET', 'POST'])
def editar_producto(request, id):
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

    return render(request, 'productos/crear_producto.html', {
        'producto_editar': producto,
        'form': form,
    })


# 4. ELIMINAR PRODUCTO
@login_required(login_url='admin_login')
@user_passes_test(es_administrador, login_url='admin_login')
@require_POST
def eliminar_producto(request, id):
    producto = get_object_or_404(Producto, id=id)
    nombres_imagenes = _nombres_imagenes(producto)
    producto.delete()
    for nombre in nombres_imagenes:
        if nombre != DEFAULT_PRODUCT_IMAGE:
            producto.imagen_principal.storage.delete(nombre)
    messages.success(request, 'Producto eliminado correctamente.')
    return redirect('lista_productos')
