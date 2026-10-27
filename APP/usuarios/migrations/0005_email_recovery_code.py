from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0004_prepare_saved_recovery_codes'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='email_recovery_code_hash',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
        migrations.AddField(
            model_name='usuario',
            name='email_recovery_code_expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
