from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('productos', '0008_repair_imagen_principal_column'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='disponible_temporada',
            field=models.BooleanField(
                default=False,
                help_text='Actívalo para mostrar este producto en la sección "Temporada" del sitio.',
                verbose_name='Disponible en temporada',
            ),
        ),
    ]
