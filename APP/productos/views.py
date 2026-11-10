from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Q
from django.http import Http404, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.http import require_POST, require_http_methods

from APP.usuarios.permissions import exigir_permiso, usuario_puede_entrar_panel
from .forms import CategoriaProductoForm, ProductoForm
from .models import CategoriaProducto, Producto, DEFAULT_PRODUCT_IMAGE


def es_administrador(user):
    return usuario_puede_entrar_panel(user)


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
def _render_admin_gestion(
    request,
    form=None,
    editor_mode='',
    producto_editar=None,
    categoria_form=None,
    editar_categoria_form=None,
    categoria_modal='',
):
    categorias = CategoriaProducto.objects.annotate(
        total_productos=Count('producto'),
    ).order_by('nombre')
    categoria_editar_id = (
        request.POST.get('categoria_id')
        if request.method == 'POST'
        else request.GET.get('editar_categoria')
    )
    categoria_seleccionada = None
    if (
        str(categoria_editar_id or '').isdecimal()
        and len(str(categoria_editar_id)) <= 18
    ):
        categoria_seleccionada = categorias.filter(
            pk=int(categoria_editar_id),
        ).first()
    query = request.GET.get('q', '').strip()[:100]
    estado = request.GET.get('estado', 'todos')
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
        'categoria_form': categoria_form or CategoriaProductoForm(),
        'editar_categoria_form': editar_categoria_form or (
            CategoriaProductoForm(
                instance=categoria_seleccionada,
                prefix=f'categoria-{categoria_seleccionada.pk}',
            )
            if categoria_seleccionada else None
        ),
        'categoria_modal': categoria_modal or (
            'editar' if categoria_seleccionada else ''
        ),
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


@login_required(login_url='login')
@user_passes_test(es_administrador, login_url='login')
@require_http_methods(['GET', 'POST'])
def gestionar_categoria_producto(request):
    if request.method == 'GET':
        query = request.GET.urlencode()
        url = reverse('lista_productos')
        return redirect(f'{url}?{query}' if query else url)

    accion = request.POST.get('accion')
    permisos = {
        'crear_categoria': 'productos.add_categoriaproducto',
        'editar_categoria': 'productos.change_categoriaproducto',
        'eliminar_categoria': 'productos.delete_categoriaproducto',
    }
    if accion in permisos:
        exigir_permiso(request, permisos[accion])

    if accion == 'crear_categoria':
        form = CategoriaProductoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría creada correctamente.')
            return redirect('lista_productos')
        return _render_admin_gestion(
            request,
            categoria_form=form,
            categoria_modal='crear',
        )

    categoria_id = request.POST.get('categoria_id', '')
    if not categoria_id.isdecimal() or len(categoria_id) > 18:
        raise Http404
    categoria = get_object_or_404(CategoriaProducto, pk=int(categoria_id))

    if accion == 'editar_categoria':
        form = CategoriaProductoForm(
            request.POST,
            instance=categoria,
            prefix=f'categoria-{categoria.pk}',
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría actualizada correctamente.')
            return redirect('lista_productos')
        return _render_admin_gestion(
            request,
            editar_categoria_form=form,
            categoria_modal='editar',
        )

    if accion == 'eliminar_categoria':
        if Producto.objects.filter(categoria=categoria).exists():
            messages.error(
                request,
                'No puedes eliminar una categoría que todavía tiene productos. '
                'Reasigna sus productos primero.',
            )
            return redirect('lista_productos')
        categoria.delete()
        messages.success(request, 'Categoría eliminada correctamente.')
        return redirect('lista_productos')

    messages.error(request, 'No se reconoció la acción solicitada.')
    return redirect('lista_productos')


def gestion_productos(request):

    if es_administrador(request.user):
        exigir_permiso(request, 'productos.view_producto')
        return _render_admin_gestion(request)

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
@login_required(login_url='login')
@user_passes_test(es_administrador, login_url='login')
@require_http_methods(['GET', 'POST'])
def crear_producto(request):
    exigir_permiso(request, 'productos.view_producto')
    exigir_permiso(request, 'productos.add_producto')
    form = ProductoForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        producto = form.save(commit=False)
        if not producto.imagen_principal:
            producto.imagen_principal = DEFAULT_PRODUCT_IMAGE
        producto.save()
        messages.success(request, 'Producto creado correctamente.')
        return redirect('lista_productos')

    if request.method == 'POST':
        messages.error(request, 'Revisa los campos marcados para corregir el formulario.')
    return _render_admin_gestion(request, form=form, editor_mode='crear')


# 3. EDITAR PRODUCTO
@login_required(login_url='login')
@user_passes_test(es_administrador, login_url='login')
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


@login_required(login_url='login')
@user_passes_test(es_administrador, login_url='login')
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
@login_required(login_url='login')
@user_passes_test(es_administrador, login_url='login')
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
