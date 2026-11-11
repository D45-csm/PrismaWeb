from decimal import Decimal

from django import forms
from django.db.models import Q
from django.forms import BaseInlineFormSet, inlineformset_factory

from APP.insumos.models import Insumo

from .models import Receta, RecetaInsumo
from .services import unidad_a_base


class RecetaForm(forms.ModelForm):
    class Meta:
        model = Receta
        fields = ['nombre', 'descripcion', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'insumo-input',
                'placeholder': 'Ej. Torta de chocolate',
                'autocomplete': 'off',
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'insumo-input',
                'placeholder': 'Describe la receta',
                'rows': 3,
            }),
            'activo': forms.CheckboxInput(),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        if not nombre:
            raise forms.ValidationError('Ingresa el nombre de la receta.')
        return nombre


class RecetaInsumoForm(forms.ModelForm):
    cantidad_insumo = forms.DecimalField(
        label='Cantidad por receta',
        min_value=Decimal('0.001'),
        max_digits=10,
        decimal_places=3,
        widget=forms.NumberInput(attrs={
            'class': 'insumo-input',
            'min': '0.001',
            'step': '0.001',
            'required': True,
        }),
    )

    class Meta:
        model = RecetaInsumo
        fields = ['insumo', 'cantidad_insumo', 'medida_insumo']
        widgets = {
            'insumo': forms.Select(attrs={
                'class': 'insumo-input',
                'data-recipe-insumo': '',
                'required': True,
            }),
            'medida_insumo': forms.Select(attrs={'class': 'insumo-input'}),
        }
        labels = {
            'insumo': 'Insumo vinculado',
            'medida_insumo': 'Unidad de la receta',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_recipe_id = self.instance.receta_id
        linked_insumos = Insumo.objects.filter(
            recetainsumo__receta_id=current_recipe_id,
        ).values_list('pk', flat=True) if current_recipe_id else ()
        self.fields['insumo'].queryset = Insumo.objects.filter(
            Q(activo=True) | Q(pk__in=linked_insumos),
        ).order_by('nombre')
        self.fields['insumo'].empty_label = 'Selecciona un insumo'
        self.fields['medida_insumo'].choices = [
            ('', 'Selecciona una unidad'),
            *self.fields['medida_insumo'].choices,
        ]

    def clean(self):
        cleaned_data = super().clean()
        insumo = cleaned_data.get('insumo')
        medida = cleaned_data.get('medida_insumo')
        if insumo and medida:
            unidad_insumo = unidad_a_base(insumo.unidad_medida)
            unidad_receta = unidad_a_base(medida)
            if not unidad_insumo or not unidad_receta:
                raise forms.ValidationError(
                    'La unidad seleccionada no permite calcular el inventario.',
                )
            if unidad_insumo[0] != unidad_receta[0]:
                self.add_error(
                    'medida_insumo',
                    'La unidad debe ser compatible con la unidad del insumo.',
                )
        return cleaned_data


class BaseRecetaInsumoFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        insumos = set()
        total = 0
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get('DELETE'):
                continue
            insumo = form.cleaned_data.get('insumo')
            if not insumo:
                continue
            total += 1
            if insumo.pk in insumos:
                raise forms.ValidationError(
                    'No repitas un insumo en la misma receta.',
                )
            insumos.add(insumo.pk)
        if total == 0:
            raise forms.ValidationError(
                'Vincula al menos un insumo para guardar la receta.',
            )


RecetaInsumoFormSet = inlineformset_factory(
    Receta,
    RecetaInsumo,
    form=RecetaInsumoForm,
    formset=BaseRecetaInsumoFormSet,
    extra=1,
    can_delete=True,
    max_num=30,
    validate_max=True,
)
