import re

from django.db import migrations, models


def normalize_username(value):
    username = (value or '').split('@')[0].strip().lower()
    username = re.sub(r'[^a-z0-9_.-]+', '_', username)
    username = username.strip('_.-')
    return username or 'usuario'


def fill_remaining_usernames(apps, schema_editor):
    Usuario = apps.get_model('core', 'Usuario')
    used_usernames = set(
        Usuario.objects
        .exclude(username__isnull=True)
        .exclude(username='')
        .values_list('username', flat=True)
    )

    usuarios = Usuario.objects.filter(username__isnull=True) | Usuario.objects.filter(username='')
    for usuario in usuarios.order_by('id'):
        base_username = normalize_username(usuario.email or usuario.nombre or f'usuario{usuario.id}')[:50]
        username = base_username
        suffix = 2

        while username in used_usernames:
            suffix_text = str(suffix)
            username = f'{base_username[:50 - len(suffix_text)]}{suffix_text}'
            suffix += 1

        usuario.username = username
        usuario.save(update_fields=['username'])
        used_usernames.add(username)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_backfill_usuario_username'),
    ]

    operations = [
        migrations.RunPython(fill_remaining_usernames, noop_reverse),
        migrations.AlterField(
            model_name='usuario',
            name='username',
            field=models.CharField(
                help_text='Nombre de usuario unico (ej: user.test)',
                max_length=50,
                unique=True,
            ),
        ),
    ]
