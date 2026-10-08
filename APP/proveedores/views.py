from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Proveedor
from .forms import ProveedorForm
# Create your views here.

@login_required
def Crear_listar(request):
    """Vista principal: Muestra la lista y procesa el formulario de creación."""
    proveedores = Proveedor.objects.all().order_by('-id')
    
    if request.method == 'POST':
        form = ProveedorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Proveedor registrado exitosamente en PRISMA.', extra_tags='crud')
            return redirect('gestion_proveedores')
        else:
            messages.error(request, 'Ocurrió un error al guardar. Verifica los datos.', extra_tags='crud')
    else:
        form = ProveedorForm()

    context = {
        'proveedores': proveedores,
        'form': form,
        'modo_edicion': False
    }
    return render(request, 'gestion_proveedores.html', context)

@login_required
def editar_proveedor(request, pk):
    """Vista de edición: Carga el proveedor en el formulario manteniendo la lista visible."""
    proveedor = get_object_or_404(Proveedor, pk=pk)
    proveedores = Proveedor.objects.all().order_by('-id')

    if request.method == 'POST':
        form = ProveedorForm(request.POST, instance=proveedor)
        if form.is_valid():
            form.save()
            messages.success(request, f'Proveedor "{proveedor.nombre}" actualizado correctamente.', extra_tags='crud')
            return redirect('gestion_proveedores')
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.', extra_tags='crud')
    else:
        form = ProveedorForm(instance=proveedor)

    context = {
        'proveedores': proveedores,
        'form': form,
        'modo_edicion': True,
        'proveedor_actual': proveedor
    }
    return render(request, 'gestion_proveedores.html', context)

@login_required
def eliminar_proveedor(request, pk):
    """Vista de eliminación: Procesa el borrado mediante POST por seguridad."""
    proveedor = get_object_or_404(Proveedor, pk=pk)
    if request.method == 'POST':
        nombre_proveedor = proveedor.nombre
        proveedor.delete()
        messages.success(request, f'El proveedor "{nombre_proveedor}" ha sido eliminado del sistema.', extra_tags='crud')
    
    return redirect('gestion_proveedores')