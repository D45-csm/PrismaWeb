from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from decimal import Decimal, InvalidOperation
from .models import Producto, CategoriaProducto


def crear_producto(request):

    categorias = CategoriaProducto.objects.all()

    if request.method == 'POST':

        print("ARCHIVOS RECIBIDOS:", request.FILES)
        print("IMAGEN PRINCIPAL:", request.FILES.get('imagen_principal'))

        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        precio = request.POST.get('precio')
        categoria_id = request.POST.get('categoria')

        imagen_principal = request.FILES.get('imagen_principal')
        imagen_2 = request.FILES.get('imagen_2')
        imagen_3 = request.FILES.get('imagen_3')
        imagen_4 = request.FILES.get('imagen_4')

        # Validar campos obligatorios
        if not nombre or not descripcion or not precio or not categoria_id:
            messages.error(
                request,
                'Por favor, completa todos los campos obligatorios.'
            )

            return render(request, 'productos/crear_producto.html', {
                'categorias': categorias,
                'productos': Producto.objects.all()
            })

        # Validar precio
        try:
            precio = Decimal(precio)

            if precio <= 0:
                messages.error(
                    request,
                    'El precio debe ser mayor que 0.'
                )

                return render(request, 'productos/crear_producto.html', {
                    'categorias': categorias,
                    'productos': Producto.objects.all()
                })

        except InvalidOperation:

            messages.error(
                request,
                'Ingresa un precio válido.'
            )

            return render(request, 'productos/crear_producto.html', {
                'categorias': categorias,
                'productos': Producto.objects.all()
            })

        # Buscar categoría
        categoria = get_object_or_404(
            CategoriaProducto,
            id=categoria_id
        )

        # Crear producto
        Producto.objects.create(
            categoria=categoria,
            nombre=nombre,
            descripcion=descripcion,
            precio=precio,
            imagen_principal=imagen_principal,
            imagen_2=imagen_2,
            imagen_3=imagen_3,
            imagen_4=imagen_4,
            activo=True
        )

        messages.success(
            request,
            'Producto creado correctamente.'
        )

        return redirect('crear_producto')

    productos = Producto.objects.all().order_by('-id')

    return render(request, 'productos/crear_producto.html', {
        'categorias': categorias,
        'productos': productos
    })


# =====================================================
# EDITAR PRODUCTO
# =====================================================

def editar_producto(request, id):

    producto = get_object_or_404(Producto, id=id)
    categorias = CategoriaProducto.objects.all()

    if request.method == 'POST':

        producto.nombre = request.POST.get('nombre')
        producto.descripcion = request.POST.get('descripcion')
        producto.precio = request.POST.get('precio')

        categoria_id = request.POST.get('categoria')

        # Validar categoría
        if categoria_id:
            producto.categoria = get_object_or_404(
                CategoriaProducto,
                id=categoria_id
            )

        # Validar precio
        try:

            precio = Decimal(producto.precio)

            if precio <= 0:
                messages.error(
                    request,
                    'El precio debe ser mayor que 0.'
                )

                return render(request, 'productos/crear_producto.html', {
                    'producto_editar': producto,
                    'categorias': categorias,
                    'productos': Producto.objects.all()
                })

            producto.precio = precio

        except (InvalidOperation, TypeError):

            messages.error(
                request,
                'Ingresa un precio válido.'
            )

            return render(request, 'productos/crear_producto.html', {
                'producto_editar': producto,
                'categorias': categorias,
                'productos': Producto.objects.all()
            })

        # ==========================================
        # ELIMINAR IMÁGENES EXISTENTES
        # ==========================================

        if request.POST.get('eliminar_imagen_principal') == '1':

            if producto.imagen_principal:
                producto.imagen_principal.delete(save=False)

            producto.imagen_principal = None

        if request.POST.get('eliminar_imagen_2') == '1':

            if producto.imagen_2:
                producto.imagen_2.delete(save=False)

            producto.imagen_2 = None

        if request.POST.get('eliminar_imagen_3') == '1':

            if producto.imagen_3:
                producto.imagen_3.delete(save=False)

            producto.imagen_3 = None

        if request.POST.get('eliminar_imagen_4') == '1':

            if producto.imagen_4:
                producto.imagen_4.delete(save=False)

            producto.imagen_4 = None

        # ==========================================
        # NUEVAS IMÁGENES
        # ==========================================

        if request.FILES.get('imagen_principal'):
            producto.imagen_principal = request.FILES.get(
                'imagen_principal'
            )

        if request.FILES.get('imagen_2'):
            producto.imagen_2 = request.FILES.get('imagen_2')

        if request.FILES.get('imagen_3'):
            producto.imagen_3 = request.FILES.get('imagen_3')

        if request.FILES.get('imagen_4'):
            producto.imagen_4 = request.FILES.get('imagen_4')

        producto.save()

        messages.success(
            request,
            'Producto actualizado correctamente.'
        )

        return redirect('crear_producto')

    productos = Producto.objects.all().order_by('-id')

    return render(request, 'productos/crear_producto.html', {
        'producto_editar': producto,
        'categorias': categorias,
        'productos': productos
    })


# =====================================================
# ELIMINAR PRODUCTO
# =====================================================

def eliminar_producto(request, id):

    producto = get_object_or_404(Producto, id=id)

    if request.method == 'POST':

        # Eliminar imágenes del almacenamiento
        if producto.imagen_principal:
            producto.imagen_principal.delete(save=False)

        if producto.imagen_2:
            producto.imagen_2.delete(save=False)

        if producto.imagen_3:
            producto.imagen_3.delete(save=False)

        if producto.imagen_4:
            producto.imagen_4.delete(save=False)

        producto.delete()

        messages.success(
            request,
            'Producto eliminado correctamente.'
        )

        return redirect('crear_producto')

    return redirect('crear_producto')