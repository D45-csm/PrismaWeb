from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from .forms import RegistroForm, LoginForm
from django.contrib import messages

# Create your views here.
def registro_view(request):
    if request.method == 'POST': #valida si el metodo es POST
        form = RegistroForm(request.POST) #instancia de RegistroForm ubicada en forms.py con los datos del POST
        if form.is_valid():  #valida cada campo del formulario
            usuario = form.save() #si todo es valido, se guarda el usuario en la base de datos
            login(request, usuario) #iniciar sesion del usuario registrado
            messages.success(request, 'Registro exitoso. ¡Bienvenido!')
            return redirect('perfil') #redirecciona a la vista base_cliente
    else:
        form = RegistroForm() #si el metodo no es POST, se crea una instancia vacia del formulario
    return render(request, 'usuarios/registro.html', {'form': form}) #renderiza la plantilla de registro con el formulario

def login_view(request):
    if request.method == 'POST': #valida si el metodo es POST
        form = LoginForm(data=request.POST) #instancia de LoginForm ubicada en forms.py con los datos del POST
        if form.is_valid():#valida cada campo del formulario
            usuario = form.get_user() #
            login(request, usuario) #iniciar sesion del usuario registrado
            messages.success(request, 'Inicio de sesión exitoso. ¡Bienvenido de nuevo!')
            return redirect('perfil') #redirecciona a la vista del perfil
    else:
        form = LoginForm()
    return render(request, 'usuarios/login.html', {'form': form})

def logout_view(request):
    logout(request) #cierra la sesion del usuario
    messages.success(request, 'Has cerrado sesión correctamente.')
    return redirect('base_cliente') #redirecciona a la vista base_cliente

@login_required
def profile_view(request):
    return render(request, 'usuarios/perfil.html') #renderiza la plantilla de perfil