from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Producto, CategoriaProducto

# Definir el límite máximo permitido según tu modelo en la BD
# Para max_digits=10 y decimal_places=2, el máximo es 99,999,999.99 (99.9 millones)
# (Si aumentaste max_digits=15 en tu modelo, cambia este valor a Decimal('999999999999.99'))
PRECIO_MAXIMO = Decimal('99999999.99')


def limpiar_precio(precio_input):
    """
    Limpia y convierte formatos de precio (ej. "$ 15.000", "15000,50", "1.500.000,00")
    a un objeto Decimal cuantizado strictly a 2 decimales para evitar corromper SQLite.
    """
    if not precio_input:
        raise ValueError('Por favor, ingresa un precio.')
    
    # Eliminar símbolo de moneda y espacios
    s = str(precio_input).replace('$', '').replace(' ', '').strip()
    
    if not s:
        raise ValueError('Por favor, ingresa un precio válido.')

    num_dots = s.count('.')
    num_commas = s.count(',')

    try:
        # Caso 1: Ambos separadores (ej: "1.500.000,50" o "1,500,000.50")
        if num_dots > 0 and num_commas > 0:
            last_dot = s.rfind('.')
            last_comma = s.rfind(',')
            if last_comma > last_dot:
                # Puntos para miles, coma para decimal ("1.500.000,50")
                s = s.replace('.', '').replace(',', '.')
            else:
                # Comas para miles, punto para decimal ("1,500,000.50")
                s = s.replace(',', '')

        # Caso 2: Solo comas (ej: "1500,50" o "1,500,000")
        elif num_commas > 0:
            if num_commas == 1:
                parts = s.split(',')
                if len(parts[1]) in (1, 2):  # Coma actuando como decimal
                    s = s.replace(',', '.')
                else:  # Coma como separador de miles
                    s = s.replace(',', '')
            else:
                s = s.replace(',', '')

        # Caso 3: Solo puntos (ej: "1.500.000" o "1500.50" o "15.000")
        elif num_dots > 0:
            if num_dots > 1:
                s = s.replace('.', '')
            else:
                parts = s.split('.')
                # Si tiene 3 dígitos tras el punto (ej: 15.000, 1.500), es separador de miles
                if len(parts[1]) == 3 and len(parts[0]) <= 4:
                    s = s.replace('.', '')

        # Convertir primero a Decimal para validar límites antes de cuantizar
        d = Decimal(s)

        # NUEVA VALIDACIÓN: Control de precio máximo
        
        if d > PRECIO_MAXIMO:
            raise ValueError(f'El precio es demasiado alto. El valor máximo permitido es ${PRECIO_MAXIMO:,.2f}.')

        # Cuantizar estrictamente a 2 decimales (ej. 15000.00)
        precio_decimal = d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        if precio_decimal <= 0:
            raise ValueError('El precio debe ser mayor que $0.')
            
        return precio_decimal

    except (InvalidOperation, TypeError, ArithmeticError):
        raise ValueError('Ingresa un precio numérico válido (ejemplo: 15000 o 15000.50).')

# 1. GESTIÓN Y LISTADO DE PRODUCTOS
def gestion_productos(request):
    productos = Producto.objects.all().order_by('-id')
    return render(request, 'productos/gestion_productos.html', {
        'productos': productos
    })


# 2. CREAR PRODUCTO
def crear_producto(request):
    categorias = CategoriaProducto.objects.all()

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        precio_input = request.POST.get('precio', '').strip()
        categoria_id = request.POST.get('categoria', '').strip()

        imagen_principal = request.FILES.get('imagen_principal')
        imagen_2 = request.FILES.get('imagen_2')
        imagen_3 = request.FILES.get('imagen_3')
        imagen_4 = request.FILES.get('imagen_4')

        # Validar campos vacíos e imágenes obligatorias al crear
        if (not nombre or not descripcion or not precio_input or not categoria_id or 
            not imagen_principal or not imagen_2 or not imagen_3 or not imagen_4):
            messages.error(
                request,
                'Debes completar todos los campos e incluir las 4 imágenes requeridas.'
            )
            return render(request, 'productos/crear_producto.html', {
                'categorias': categorias,
                'nombre': nombre,
                'descripcion': descripcion,
                'precio': precio_input,
                'categoria_id': int(categoria_id) if categoria_id.isdigit() else None,
            })

        # Limpiar y validar precio
        try:
            precio_decimal = limpiar_precio(precio_input)
        except ValueError as err:
            messages.error(request, str(err))
            return render(request, 'productos/crear_producto.html', {
                'categorias': categorias,
                'nombre': nombre,
                'descripcion': descripcion,
                'precio': precio_input,
                'categoria_id': int(categoria_id) if categoria_id.isdigit() else None,
            })

        categoria = get_object_or_404(CategoriaProducto, id=categoria_id)

        Producto.objects.create(
            categoria=categoria,
            nombre=nombre,
            descripcion=descripcion,
            precio=precio_decimal,
            imagen_principal=imagen_principal,
            imagen_2=imagen_2,
            imagen_3=imagen_3,
            imagen_4=imagen_4,
            activo=True
        )

        messages.success(request, 'Producto creado correctamente.')
        return redirect('gestion_productos')

    return render(request, 'productos/crear_producto.html', {
        'categorias': categorias,
    })


# 3. EDITAR PRODUCTO
def editar_producto(request, id):
    producto = get_object_or_404(Producto, id=id)
    categorias = CategoriaProducto.objects.all()

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        precio_input = request.POST.get('precio', '').strip()
        categoria_id = request.POST.get('categoria', '').strip()

        # Validar campos requeridos
        if not nombre or not descripcion or not precio_input or not categoria_id:
            messages.error(request, 'Por favor, completa todos los campos obligatorios.')
            return render(request, 'productos/crear_producto.html', {
                'producto_editar': producto,
                'categorias': categorias,
            })

        # Limpiar y validar el precio al editar
        try:
            precio_decimal = limpiar_precio(precio_input)
        except ValueError as err:
            messages.error(request, str(err))
            return render(request, 'productos/crear_producto.html', {
                'producto_editar': producto,
                'categorias': categorias,
            })

        # Actualizar campos básicos
        producto.nombre = nombre
        producto.descripcion = descripcion
        producto.precio = precio_decimal
        producto.categoria = get_object_or_404(CategoriaProducto, id=categoria_id)

        # ELIMINAR IMÁGENES SI SE SOLICITÓ
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

        # CARGAR NUEVAS IMÁGENES SI SE ADJUNTARON
        if request.FILES.get('imagen_principal'):
            producto.imagen_principal = request.FILES.get('imagen_principal')

        if request.FILES.get('imagen_2'):
            producto.imagen_2 = request.FILES.get('imagen_2')

        if request.FILES.get('imagen_3'):
            producto.imagen_3 = request.FILES.get('imagen_3')

        if request.FILES.get('imagen_4'):
            producto.imagen_4 = request.FILES.get('imagen_4')

        # Verificar que conserve al menos la imagen principal
        if not producto.imagen_principal:
            messages.error(request, 'El producto debe conservar la imagen principal.')
            return render(request, 'productos/crear_producto.html', {
                'producto_editar': producto,
                'categorias': categorias,
            })

        producto.save()

        messages.success(request, 'Producto actualizado correctamente.')
        return redirect('gestion_productos')

    return render(request, 'productos/crear_producto.html', {
        'producto_editar': producto,
        'categorias': categorias,
    })


# 4. ELIMINAR PRODUCTO
def eliminar_producto(request, id):
    producto = get_object_or_404(Producto, id=id)

    if request.method == 'POST':
        if producto.imagen_principal:
            producto.imagen_principal.delete(save=False)

        if producto.imagen_2:
            producto.imagen_2.delete(save=False)

        if producto.imagen_3:
            producto.imagen_3.delete(save=False)

        if producto.imagen_4:
            producto.imagen_4.delete(save=False)

        producto.delete()

        messages.success(request, 'Producto eliminado correctamente.')

    return redirect('gestion_productos')