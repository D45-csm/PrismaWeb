from django.db import migrations


CLIENT_ROLE_NAME = 'Cliente'


def create_client_role_and_assign_existing_customers(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Usuario = apps.get_model('usuarios', 'Usuario')
    database = schema_editor.connection.alias

    client_role, _ = Group.objects.using(database).get_or_create(
        name=CLIENT_ROLE_NAME,
    )
    client_role.permissions.clear()

    customers_without_role = Usuario.objects.using(database).filter(
        is_staff=False,
        is_superuser=False,
        groups__isnull=True,
    ).distinct()
    for customer in customers_without_role.iterator():
        customer.groups.add(client_role)


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('usuarios', '0006_usuario_admin_recovery_code_sent_at'),
    ]

    operations = [
        migrations.RunPython(
            create_client_role_and_assign_existing_customers,
            migrations.RunPython.noop,
        ),
    ]
