from django.shortcuts import render

def productos_view(request):
    return render(request, 'productos/productos.html')

def temporada_view(request):
    return render(request, 'productos/temporada.html')