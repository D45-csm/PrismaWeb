from django.db import migrations


def associate_receipts_with_reservations(apps, schema_editor):
    Comprobante = apps.get_model('ventas', 'Comprobante')
    Venta = apps.get_model('ventas', 'Venta')
    database = schema_editor.connection.alias
    Through = Venta.comprobantes.through

    receipt_reservations = {}
    for venta_id, comprobante_id in Through.objects.using(database).values_list(
        'venta_id', 'comprobante_id'
    ):
        reserva_id = (
            Venta.objects.using(database)
            .filter(pk=venta_id)
            .values_list('reserva_id', flat=True)
            .first()
        )
        if reserva_id is None:
            raise RuntimeError(
                f'El comprobante {comprobante_id} está asociado a la venta '
                f'{venta_id}, que no tiene reserva vinculada.'
            )

        previous_reserva_id = receipt_reservations.get(comprobante_id)
        if previous_reserva_id not in (None, reserva_id):
            raise RuntimeError(
                f'El comprobante {comprobante_id} está asociado a ventas de '
                'reservas distintas y no se puede migrar automáticamente.'
            )
        receipt_reservations[comprobante_id] = reserva_id

    for comprobante_id, reserva_id in receipt_reservations.items():
        existing_reserva_id = (
            Comprobante.objects.using(database)
            .filter(pk=comprobante_id)
            .values_list('reserva_id', flat=True)
            .first()
        )
        if existing_reserva_id not in (None, reserva_id):
            raise RuntimeError(
                f'El comprobante {comprobante_id} ya está asociado a una '
                'reserva distinta de la venta vinculada.'
            )
        Comprobante.objects.using(database).filter(
            pk=comprobante_id,
            reserva_id__isnull=True,
        ).update(reserva_id=reserva_id)


class Migration(migrations.Migration):
    dependencies = [
        ('ventas', '0002_comprobante_reserva'),
    ]

    operations = [
        migrations.RunPython(
            associate_receipts_with_reservations,
            migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name='venta',
            name='comprobantes',
        ),
    ]
