from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import ProveedorForm
from .models import Proveedor


class AdministradorRequeridoMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = 'admin_login'

    def test_func(self):
        user = self.request.user
        return user.is_staff or user.is_superuser


class TituloProveedorMixin:
    titulo = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = self.titulo
        return context


class ProveedorListView(AdministradorRequeridoMixin, TituloProveedorMixin, ListView):
    model = Proveedor
    template_name = 'proveedores/proveedor_list.html'
    context_object_name = 'proveedores'
    ordering = ['nombre']
    titulo = 'Gestión de proveedores'


class ProveedorCreateView(
    AdministradorRequeridoMixin,
    TituloProveedorMixin,
    SuccessMessageMixin,
    CreateView,
):
    model = Proveedor
    form_class = ProveedorForm
    template_name = 'proveedores/proveedor_form.html'
    success_url = reverse_lazy('proveedores_lista')
    success_message = 'Proveedor creado correctamente.'
    titulo = 'Crear proveedor'


class ProveedorUpdateView(
    AdministradorRequeridoMixin,
    TituloProveedorMixin,
    SuccessMessageMixin,
    UpdateView,
):
    model = Proveedor
    form_class = ProveedorForm
    template_name = 'proveedores/proveedor_form.html'
    success_url = reverse_lazy('proveedores_lista')
    success_message = 'Proveedor actualizado correctamente.'
    titulo = 'Editar proveedor'


class ProveedorDeleteView(AdministradorRequeridoMixin, TituloProveedorMixin, DeleteView):
    model = Proveedor
    template_name = 'proveedores/proveedor_confirm_delete.html'
    success_url = reverse_lazy('proveedores_lista')
    titulo = 'Eliminar proveedor'

    def form_valid(self, form):
        nombre = self.object.nombre
        response = super().form_valid(form)
        messages.success(self.request, f'Se eliminó el proveedor {nombre}.')
        return response
