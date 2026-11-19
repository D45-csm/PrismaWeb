from decimal import Decimal

from django import forms

from APP.insumos.models import Insumo

from .models import Movimiento


class MovimientoManualForm(forms.Form):
    modo = forms.ChoiceField(
        choices=[
            ('movimiento', 'Ajuste por movimiento'),
            ('conteo', 'Conteo físico'),
        ],
        widget=forms.Select(attrs={'class': 'insumo-input', 'id': 'manualModo'}),
    )
    insumo = forms.ModelChoiceField(
        queryset=Insumo.objects.none(),
        widget=forms.Select(attrs={'class': 'insumo-input'}),
    )
    tipo_accion = forms.ChoiceField(
        choices=Movimiento.tipo_accion,
        required=False,
        widget=forms.Select(attrs={
            'class': 'insumo-input',
            'id': 'manualTipoAccion',
        }),
    )
    cantidad = forms.DecimalField(
        max_digits=10,
        decimal_places=3,
        min_value=Decimal('0'),
        widget=forms.NumberInput(attrs={
            'class': 'insumo-input',
            'min': '0',
            'step': '0.001',
            'id': 'manualCantidad',
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['insumo'].queryset = Insumo.objects.filter(
            activo=True,
        ).order_by('nombre')
        self.fields['insumo'].empty_label = 'Selecciona un insumo'
        self.fields['modo'].label = 'Tipo de operación'
        self.fields['insumo'].label = 'Insumo'
        self.fields['tipo_accion'].label = 'Movimiento'
        self.fields['cantidad'].label = 'Cantidad'

    def clean(self):
        cleaned_data = super().clean()
        modo = cleaned_data.get('modo')
        cantidad = cleaned_data.get('cantidad')
        tipo_accion = cleaned_data.get('tipo_accion')

        if modo == 'movimiento':
            if not tipo_accion:
                self.add_error('tipo_accion', 'Selecciona una entrada o salida.')
            if cantidad is not None and cantidad <= 0:
                self.add_error('cantidad', 'La cantidad debe ser mayor que cero.')
        return cleaned_data
