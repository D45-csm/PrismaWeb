from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0002_usuario_recovery_code_hash'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='recovery_code_created_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='usuario',
            name='recovery_code_attempts',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='usuario',
            name='recovery_reset_grant_hash',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
        migrations.AddField(
            model_name='usuario',
            name='recovery_reset_grant_expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
