from html import escape
from io import BytesIO
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from APP.insumos.models import Insumo
from APP.usuarios.permissions import (
    exigir_permiso,
    usuario_puede_acceder,
    usuario_puede_entrar_panel,
)

from .forms import MovimientoManualForm
from .models import Movimiento
from .services import cantidades_en_base, stock_en_unidad, unidad_a_base


MAX_CANTIDAD_MOVIMIENTO = Decimal('9999999.999')


def es_administrador(user):
    return usuario_puede_entrar_panel(user)


def _filas_inventario(query='', filtro_stock=''):
    insumos = Insumo.objects.select_related('categoria')
    if query:
        insumos = insumos.filter(
            Q(nombre__icontains=query)
            | Q(categoria__nombre__icontains=query),
        )
    insumos = list(insumos.order_by('nombre'))
    stocks = cantidades_en_base([insumo.pk for insumo in insumos])
    filas = []
    for insumo in insumos:
        stock = stock_en_unidad(
            insumo.pk,
            insumo.unidad_medida,
            stocks,
        )
        fila = {
            'insumo': insumo,
            'stock': stock,
            'stock_bajo': (
                insumo.stock_minimo > 0
                and stock <= insumo.stock_minimo
            ),
        }
        if filtro_stock != 'bajo' or fila['stock_bajo']:
            filas.append(fila)
    return filas


def _render_inventario(
    request,
    form=None,
    manual_dialog_open=False,
    query=None,
    filtro_stock=None,
):
    query = request.GET.get('q', '').strip()[:100] if query is None else query
    filtro_stock = (
        request.GET.get('stock', '')
        if filtro_stock is None else filtro_stock
    )
    if filtro_stock not in ('', 'bajo'):
        filtro_stock = ''
    filas = _filas_inventario(query, filtro_stock)

    return render(request, 'inventario/inventario_dashboard.html', {
        'filas_inventario': filas,
        'query': query,
        'filtro_stock': filtro_stock,
        'hay_filtros': bool(query or filtro_stock),
        'manual_form': form or MovimientoManualForm(),
        'manual_dialog_open': manual_dialog_open,
        'puede_ajustar': usuario_puede_acceder(
            request.user,
            'inventario.add_movimiento',
        ),
    })


@login_required(login_url='login')
@user_passes_test(es_administrador, login_url='login')
@require_http_methods(['GET', 'POST'])
def inventario_dashboard(request):
    exigir_permiso(request, 'insumos.view_insumo')

    if request.method == 'GET':
        return _render_inventario(request)

    exigir_permiso(request, 'inventario.add_movimiento')
    form = MovimientoManualForm(request.POST)
    if not form.is_valid():
        return _render_inventario(
            request,
            form=form,
            manual_dialog_open=True,
        )

    insumo_id = form.cleaned_data['insumo'].pk
    cantidad = form.cleaned_data['cantidad']
    modo = form.cleaned_data['modo']
    tipo_accion = form.cleaned_data['tipo_accion']
    mensaje_error = None

    with transaction.atomic():
        insumo = get_object_or_404(
            Insumo.objects.select_for_update(),
            pk=insumo_id,
            activo=True,
        )
        stocks = cantidades_en_base([insumo.pk])
        stock_actual = stock_en_unidad(
            insumo.pk,
            insumo.unidad_medida,
            stocks,
        )

        if modo == 'conteo':
            diferencia = cantidad - stock_actual
        else:
            diferencia = (
                cantidad
                if tipo_accion == 'ENTRADA'
                else -cantidad
            )
            if diferencia < 0 and cantidad > max(stock_actual, Decimal('0')):
                mensaje_error = (
                    'La salida no puede ser mayor que el stock disponible.'
                )

        if not mensaje_error and diferencia:
            cantidad_movimiento = abs(diferencia)
            try:
                cantidad_movimiento = cantidad_movimiento.quantize(
                    Decimal('0.001'),
                )
            except InvalidOperation:
                mensaje_error = 'La cantidad no se puede registrar.'
            if (
                not mensaje_error
                and cantidad_movimiento != abs(diferencia)
            ):
                mensaje_error = (
                    'La diferencia no cabe en la precisión de tres decimales '
                    'del inventario.'
                )
            elif (
                not mensaje_error
                and cantidad_movimiento > MAX_CANTIDAD_MOVIMIENTO
            ):
                mensaje_error = (
                    'La cantidad supera el máximo registrable en un movimiento.'
                )

            if not mensaje_error:
                Movimiento.objects.create(
                    origen='AJUSTE',
                    accion='ENTRADA' if diferencia > 0 else 'SALIDA',
                    usuario=request.user,
                    insumo=insumo,
                    cantidad=cantidad_movimiento,
                    unidad_medida=insumo.unidad_medida,
                )

    if mensaje_error:
        form.add_error('cantidad', mensaje_error)
        return _render_inventario(
            request,
            form=form,
            manual_dialog_open=True,
        )

    if diferencia:
        messages.success(
            request,
            'El movimiento manual se registró correctamente.',
        )
    else:
        messages.info(
            request,
            'El conteo coincide con el stock registrado; no se creó ningún movimiento.',
        )
    return redirect('inventario_dashboard')


@login_required(login_url='login')
@user_passes_test(es_administrador, login_url='login')
@require_http_methods(['GET'])
def historial_movimientos(request):
    exigir_permiso(request, 'insumos.view_insumo')
    movimientos = Movimiento.objects.select_related(
        'insumo', 'usuario', 'anulado_por',
    ).order_by('-fecha_movimiento', '-pk')
    pagina = Paginator(movimientos, 50).get_page(request.GET.get('page'))
    return render(request, 'inventario/historial_movimientos.html', {
        'pagina': pagina,
        'puede_anular': usuario_puede_acceder(
            request.user,
            'inventario.change_movimiento',
        ),
    })


@login_required(login_url='login')
@user_passes_test(es_administrador, login_url='login')
@require_http_methods(['POST'])
def anular_movimiento(request, pk):
    exigir_permiso(request, 'inventario.change_movimiento')
    motivo = request.POST.get('motivo', '').strip()
    if not motivo:
        messages.error(request, 'Indica el motivo para anular el movimiento.')
        return redirect('historial_movimientos')
    if len(motivo) > 500:
        messages.error(request, 'El motivo no puede superar 500 caracteres.')
        return redirect('historial_movimientos')

    with transaction.atomic():
        movimiento = get_object_or_404(
            Movimiento.objects.select_for_update().select_related('insumo'),
            pk=pk,
        )
        if movimiento.estado == Movimiento.Estado.ANULADO:
            messages.error(request, 'Este movimiento ya fue anulado.')
            return redirect('historial_movimientos')

        insumo = Insumo.objects.select_for_update().get(pk=movimiento.insumo_id)
        if movimiento.accion == 'ENTRADA':
            movimiento_conversion = unidad_a_base(movimiento.unidad_medida)
            insumo_conversion = unidad_a_base(insumo.unidad_medida)
            if (
                movimiento_conversion
                and insumo_conversion
                and movimiento_conversion[0] == insumo_conversion[0]
            ):
                stock_actual = stock_en_unidad(
                    insumo.pk,
                    insumo.unidad_medida,
                    cantidades_en_base([insumo.pk]),
                )
                cantidad_a_retirar = (
                    movimiento.cantidad
                    * movimiento_conversion[1]
                    / insumo_conversion[1]
                )
                if stock_actual - cantidad_a_retirar < 0:
                    messages.error(
                        request,
                        'No se puede anular esta entrada porque parte de ese '
                        'stock ya fue consumido. Registra un ajuste de salida '
                        'si necesitas corregir el saldo.',
                    )
                    return redirect('historial_movimientos')

        movimiento.estado = Movimiento.Estado.ANULADO
        movimiento.motivo_anulacion = motivo
        movimiento.fecha_anulacion = timezone.now()
        movimiento.anulado_por = request.user
        movimiento.save(update_fields=[
            'estado',
            'motivo_anulacion',
            'fecha_anulacion',
            'anulado_por',
        ])

    messages.success(
        request,
        'El movimiento fue anulado y el stock se recalculó correctamente.',
    )
    return redirect('historial_movimientos')


@login_required(login_url='login')
@user_passes_test(es_administrador, login_url='login')
@require_http_methods(['GET'])
def exportar_inventario_pdf(request):
    exigir_permiso(request, 'insumos.view_insumo')
    filas = _filas_inventario()
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=landscape(letter),
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title='Reporte de inventario',
        author='Prisma',
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='InventoryReportSubtitle',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        textColor=colors.HexColor('#6f6878'),
        spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name='InventoryReportCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#302a38'),
    ))
    styles.add(ParagraphStyle(
        name='InventoryReportHeader',
        parent=styles['InventoryReportCell'],
        fontName='Helvetica-Bold',
        textColor=colors.white,
    ))
    story = [
        Paragraph('Reporte de inventario', styles['Title']),
        Paragraph(
            f'Generado el {timezone.localtime():%d/%m/%Y %H:%M}',
            styles['InventoryReportSubtitle'],
        ),
    ]
    headers = [
        'Insumo',
        'Categoría',
        'Stock actual',
        'Unidad de medida',
        'Stock mínimo',
        'Estado del stock',
        'Disponibilidad',
    ]
    table_data = [[
        Paragraph(header, styles['InventoryReportHeader'])
        for header in headers
    ]]
    for fila in filas:
        insumo = fila['insumo']
        values = [
            insumo.nombre,
            insumo.categoria.nombre,
            format(fila['stock'], 'f'),
            insumo.get_unidad_medida_display(),
            format(insumo.stock_minimo, 'f'),
            'Stock bajo' if fila['stock_bajo'] else 'Disponible',
            'Activo' if insumo.activo else 'Desactivado',
        ]
        table_data.append([
            Paragraph(escape(str(value)), styles['InventoryReportCell'])
            for value in values
        ])

    column_widths = [43 * mm, 34 * mm, 27 * mm, 36 * mm, 27 * mm, 32 * mm, 31 * mm]
    table = Table(
        table_data,
        colWidths=column_widths,
        repeatRows=1,
        hAlign='LEFT',
    )
    table_styles = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#433154')),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#ded8e5')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 7),
        ('RIGHTPADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]
    for row_index, fila in enumerate(filas, start=1):
        if fila['stock_bajo']:
            table_styles.append((
                'BACKGROUND',
                (0, row_index),
                (-1, row_index),
                colors.HexColor('#fff2bd'),
            ))
        elif row_index % 2 == 0:
            table_styles.append((
                'BACKGROUND',
                (0, row_index),
                (-1, row_index),
                colors.HexColor('#f8f6fb'),
            ))
    table.setStyle(TableStyle(table_styles))
    story.extend([
        Paragraph(f'Total de insumos: {len(filas)}', styles['Normal']),
        Spacer(1, 5 * mm),
        table,
    ])
    document.build(story)

    response = HttpResponse(output.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_inventario.pdf"'
    return response
