from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('insumos', '0003_insumo_proveedor_referencia'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='insumo',
            name='proveedor_referencia',
        ),
    ]
