from decimal import Decimal

import django.db.models.deletion
from django.db import migrations, models


LEGACY_PRICES = {
    'Manzana Verde Cheesecake': Decimal('25000.00'),
    'Café Chocolate': Decimal('28000.00'),
    'Fresa Chocolate': Decimal('32000.00'),
    'Postre Personalizado': Decimal('0.00'),
}


def migrate_reservation_products(apps, schema_editor):
    Reserva = apps.get_model('reserva', 'Reserva')
    DetalleReserva = apps.get_model('reserva', 'DetalleReserva')
    Producto = apps.get_model('productos', 'Producto')
    database = schema_editor.connection.alias

    for detail in DetalleReserva.objects.using(database).select_related('producto').all():
        if not detail.nombre_producto:
            detail.nombre_producto = (
                detail.producto.nombre if detail.producto_id else 'Producto reservado'
            )
            detail.save(update_fields=['nombre_producto'], using=database)

    for reserva in Reserva.objects.using(database).all():
        if not reserva.postre or reserva.lineas.exists():
            continue

        producto = Producto.objects.using(database).filter(
            nombre__iexact=reserva.postre
        ).first()
        precio = LEGACY_PRICES.get(
            reserva.postre,
            producto.precio if producto else Decimal('0.00'),
        )
        DetalleReserva.objects.using(database).create(
            reserva_id=reserva.pk,
            producto_id=producto.pk if producto else None,
            nombre_producto=reserva.postre,
            cantidad=reserva.cantidad,
            precio_unitario=precio,
        )


class Migration(migrations.Migration):
    dependencies = [
        ('productos', '0010_merge_20261022_1059'),
        ('reserva', '0004_detallereserva'),
    ]

    operations = [
        migrations.AddField(
            model_name='detallereserva',
            name='nombre_producto',
            field=models.CharField(max_length=120, null=True),
        ),
        migrations.AlterField(
            model_name='detallereserva',
            name='producto',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='detalles_reserva',
                to='productos.producto',
            ),
        ),
        migrations.RunPython(migrate_reservation_products, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='reserva',
            name='postre',
        ),
        migrations.RemoveField(
            model_name='reserva',
            name='cantidad',
        ),
        migrations.AlterField(
            model_name='detallereserva',
            name='nombre_producto',
            field=models.CharField(max_length=120),
        ),
    ]
