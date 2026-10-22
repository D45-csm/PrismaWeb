from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.text import slugify
from django.views.decorators.http import require_POST, require_http_methods

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
def gestion_productos(request):

    if es_administrador(request.user):
        productos = Producto.objects.all().order_by('-id')
        return render(request, 'productos/gestion_productos.html', {
            'productos': productos
        })

    # Los clientes ven el catálogo completo (con buscador, filtros y modal).
    return redirect('productos')


def _producto_a_json(producto):
    """Convierte un Producto a un dict apto para el catálogo en JavaScript."""
    imagenes = [
        imagen.url
        for imagen in (
            producto.imagen_principal,
            producto.imagen_2,
            producto.imagen_3,
            producto.imagen_4,
        )
        if imagen
    ]
    if not imagenes:
        imagenes = ['']

    return {
        'id': producto.id,
        'nombre': producto.nombre,
        'desc': producto.descripcion,
        'precio': float(producto.precio),
        'categoria': slugify(producto.categoria.nombre) if producto.categoria_id else 'otros',
        'img': imagenes[0],
        'imgs': imagenes,
    }


def _categorias_disponibles(productos_qs):
    """Categorías (con su slug) presentes en un queryset de productos activos."""
    nombres = (
        CategoriaProducto.objects.filter(producto__in=productos_qs)
        .distinct()
        .order_by('nombre')
        .values_list('nombre', flat=True)
    )
    return [{'nombre': nombre, 'slug': slugify(nombre)} for nombre in nombres]


# 1-B. CATÁLOGO PÚBLICO DE PRODUCTOS (CLIENTES)
@require_http_methods(['GET'])
def productos_view(request):
    productos_qs = (
        Producto.objects.filter(activo=True)
        .select_related('categoria')
        .order_by('-id')
    )
    contexto = {
        'productos': productos_qs,
        'categorias': _categorias_disponibles(productos_qs),
        'productos_data': [_producto_a_json(p) for p in productos_qs],
    }
    return render(request, 'productos/productos.html', contexto)


# 1-C. CATÁLOGO DE TEMPORADA (CLIENTES)
@require_http_methods(['GET'])
def temporada_view(request):
    productos_qs = (
        Producto.objects.filter(activo=True, disponible_temporada=True)
        .select_related('categoria')
        .order_by('-id')
    )
    contexto = {
        'productos': productos_qs,
        'temporada_data': [_producto_a_json(p) for p in productos_qs],
    }
    return render(request, 'productos/temporada.html', contexto)


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
