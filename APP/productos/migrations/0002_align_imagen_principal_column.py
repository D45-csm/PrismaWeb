from django.db import migrations, models


def _align_image_column(apps, schema_editor, source_column, target_column):
    producto = apps.get_model('productos', 'Producto')
    with schema_editor.connection.cursor() as cursor:
        columns = {
            column.name
            for column in schema_editor.connection.introspection.get_table_description(
                cursor,
                producto._meta.db_table,
            )
        }

    if target_column in columns:
        return
    if source_column not in columns:
        raise RuntimeError(
            f'No se encontró la columna {source_column} ni {target_column} '
            f'en {producto._meta.db_table}.'
        )

    old_field = producto._meta.get_field('imagen')
    new_field = old_field.clone()
    new_field.db_column = target_column
    new_field.set_attributes_from_name(old_field.name)
    new_field.model = producto
    schema_editor.alter_field(producto, old_field, new_field, strict=True)


def align_image_column(apps, schema_editor):
    _align_image_column(apps, schema_editor, 'imagen', 'imagen_principal')


def restore_image_column(apps, schema_editor):
    _align_image_column(apps, schema_editor, 'imagen_principal', 'imagen')


class Migration(migrations.Migration):

    dependencies = [
        ('productos', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    align_image_column,
                    restore_image_column,
                ),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name='producto',
                    name='imagen',
                    field=models.ImageField(
                        db_column='imagen_principal',
                        upload_to='productos/',
                    ),
                ),
            ],
        ),
    ]
