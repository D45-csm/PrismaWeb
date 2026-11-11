from decimal import Decimal

from APP.inventario.models import Movimiento


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


def maximo_para_insumo(receta_insumo, stocks):
    unidad_receta = unidad_a_base(receta_insumo.medida_insumo)
    unidad_stock = unidad_a_base(receta_insumo.insumo.unidad_medida)
    if (
        not unidad_receta
        or not unidad_stock
        or unidad_receta[0] != unidad_stock[0]
    ):
        return 0
    dimension, factor = unidad_receta
    cantidad_requerida = Decimal(str(receta_insumo.cantidad_insumo)) * factor
    if cantidad_requerida <= 0:
        return 0
    stock = max(
        Decimal('0'),
        stocks.get((receta_insumo.insumo_id, dimension), Decimal('0')),
    )
    return int(stock // cantidad_requerida)


def resumen_recetas(recetas):
    filas_por_receta = {
        receta.pk: list(
            receta.recetainsumo_set.all(),
        )
        for receta in recetas
    }
    insumo_ids = {
        fila.insumo_id
        for filas in filas_por_receta.values()
        for fila in filas
    }
    stocks = cantidades_en_base(insumo_ids)
    resumen = []

    for receta in recetas:
        filas = filas_por_receta[receta.pk]
        ingredientes = []
        limites = []
        for fila in filas:
            unidad = unidad_a_base(fila.medida_insumo)
            dimension = unidad[0] if unidad else None
            limite = maximo_para_insumo(fila, stocks)
            limites.append(limite)
            stock_base = stocks.get(
                (fila.insumo_id, dimension),
                Decimal('0'),
            ) if dimension else Decimal('0')
            cantidad_stock = (
                stock_base / unidad[1]
                if unidad else Decimal('0')
            )
            ingredientes.append({
                'nombre': fila.insumo.nombre,
                'cantidad': fila.cantidad_insumo,
                'unidad': fila.get_medida_insumo_display(),
                'stock': max(Decimal('0'), cantidad_stock),
            })

        resumen.append({
            'receta': receta,
            'ingredientes': ingredientes,
            'maximo': min(limites) if limites else 0,
        })
    return resumen, stocks


def cantidad_para_movimiento(receta_insumo, veces):
    unidad_receta = unidad_a_base(receta_insumo.medida_insumo)
    unidad_stock = unidad_a_base(receta_insumo.insumo.unidad_medida)
    if (
        not unidad_receta
        or not unidad_stock
        or unidad_receta[0] != unidad_stock[0]
    ):
        raise ValueError(
            f'No se puede convertir la unidad de {receta_insumo.insumo.nombre}.',
        )

    cantidad_base = (
        Decimal(str(receta_insumo.cantidad_insumo))
        * unidad_receta[1]
        * veces
    )
    cantidad_stock = cantidad_base / unidad_stock[1]
    cantidad_redondeada = cantidad_stock.quantize(Decimal('0.001'))
    if cantidad_redondeada != cantidad_stock or cantidad_redondeada <= 0:
        raise ValueError(
            f'La cantidad de {receta_insumo.insumo.nombre} supera la '
            'precisión de tres decimales del inventario.',
        )
    if cantidad_redondeada > Decimal('9999999.999'):
        raise ValueError(
            f'La cantidad de {receta_insumo.insumo.nombre} supera el máximo '
            'registrable en un movimiento de inventario.',
        )
    return cantidad_redondeada
