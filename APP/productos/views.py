from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Producto, CategoriaProducto
from decimal import Decimal, InvalidOperation


def crear_producto(request):

    if request.method == 'POST':

        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        precio = request.POST.get('precio')
        categoria_id = request.POST.get('categoria')
        imagen = request.FILES.get('imagen')

        # Validar campos obligatorios
        if not nombre or not descripcion or not precio or not categoria_id:
            messages.error(request, 'Por favor, completa todos los campos obligatorios.')
            categorias = CategoriaProducto.objects.all()
            return render(request, 'productos/crear_producto.html', {
                'categorias': categorias
            })

        # Validar precio
        try:
            precio = Decimal(precio)

            if precio <= 0:
                messages.error(request, 'El precio debe ser mayor que 0.')
                categorias = CategoriaProducto.objects.all()
                return render(request, 'productos/crear_producto.html', {
                    'categorias': categorias
                })

        except InvalidOperation:
            messages.error(request, 'Ingresa un precio válido.')
            categorias = CategoriaProducto.objects.all()
            return render(request, 'productos/crear_producto.html', {
                'categorias': categorias
            })

        # Buscar la categoría
        try:
            categoria = CategoriaProducto.objects.get(id=categoria_id)
        except CategoriaProducto.DoesNotExist:
            messages.error(request, 'La categoría seleccionada no existe.')
            categorias = CategoriaProducto.objects.all()
            return render(request, 'productos/crear_producto.html', {
                'categorias': categorias
            })

        # Crear producto
        Producto.objects.create(
            categoria=categoria,
            nombre=nombre,
            descripcion=descripcion,
            imagen=imagen,
            precio=precio,
            activo=True
        )

        messages.success(request, 'Producto creado correctamente.')

        return redirect('crear_producto')

    categorias = CategoriaProducto.objects.all()

    return render(request, 'productos/crear_producto.html', {
        'categorias': categorias
    })