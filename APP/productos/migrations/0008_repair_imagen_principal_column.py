from django.db import migrations


DEFAULT_PRODUCT_IMAGE = 'productos/imagen_por_defecto.svg'


def restore_imagen_principal_column(apps, schema_editor):
    producto = apps.get_model('productos', 'Producto')
    table_name = producto._meta.db_table

    with schema_editor.connection.cursor() as cursor:
        columns = {
            column.name
            for column in schema_editor.connection.introspection.get_table_description(
                cursor,
                table_name,
            )
        }

    if 'imagen_principal' not in columns:
        field = producto._meta.get_field('imagen_principal')
        schema_editor.add_field(producto, field)

        producto.objects.filter(imagen_principal__isnull=True).update(
            imagen_principal=DEFAULT_PRODUCT_IMAGE,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('productos', '0007_remove_producto_imagen'),
    ]

    operations = [
        migrations.RunPython(
            restore_imagen_principal_column,
            migrations.RunPython.noop,
        ),
    ]
