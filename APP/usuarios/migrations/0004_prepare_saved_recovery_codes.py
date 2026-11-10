from django.db import migrations, models


def clear_email_codes(apps, schema_editor):
    Usuario = apps.get_model('usuarios', 'Usuario')
    Usuario.objects.using(schema_editor.connection.alias).update(
        recovery_code_hash='',
        recovery_code_attempts=0,
        recovery_code_locked_until=None,
        recovery_reset_grant_hash='',
        recovery_reset_grant_expires_at=None,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0003_recovery_code_expiry_and_reset_grant'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='recovery_code_locked_until',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(clear_email_codes, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='usuario',
            name='recovery_code_created_at',
        ),
    ]
