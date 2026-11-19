from decimal import Decimal

from .models import Movimiento


UNIDADES_BASE = {
    'g': ('masa', Decimal('1')),
    'kg': ('masa', Decimal('1000')),
    'ml': ('volumen', Decimal('1')),
    'l': ('volumen', Decimal('1000')),
    'u': ('unidad', Decimal('1')),
}


def unidad_a_base(unidad):
    return UNIDADES_BASE.get(unidad)


def unidades_compatibles(unidad):
    conversion = unidad_a_base(unidad)
    if not conversion:
        return []
    dimension = conversion[0]
    return [
        codigo
        for codigo, (tipo, _factor) in UNIDADES_BASE.items()
        if tipo == dimension
    ]


def cantidades_en_base(insumo_ids):
    stocks = {}
    movimientos = Movimiento.objects.filter(
        insumo_id__in=insumo_ids,
        estado=Movimiento.Estado.ACTIVO,
    ).values_list('insumo_id', 'accion', 'cantidad', 'unidad_medida')

    for insumo_id, accion, cantidad, unidad in movimientos:
        conversion = unidad_a_base(unidad)
        if not conversion:
            continue
        dimension, factor = conversion
        signo = Decimal('1') if accion == 'ENTRADA' else Decimal('-1')
        clave = (insumo_id, dimension)
        stocks[clave] = (
            stocks.get(clave, Decimal('0'))
            + Decimal(cantidad) * factor * signo
        )
    return stocks


def stock_en_unidad(insumo_id, unidad, stocks):
    conversion = unidad_a_base(unidad)
    if not conversion:
        return Decimal('0')
    dimension, factor = conversion
    return stocks.get((insumo_id, dimension), Decimal('0')) / factor
