from django.db import migrations


def backfill_usuario_username(apps, schema_editor):
    Perfil = apps.get_model('core', 'Perfil')
    Usuario = apps.get_model('core', 'Usuario')

    used_usernames = set(
        Usuario.objects
        .exclude(username__isnull=True)
        .exclude(username='')
        .values_list('username', flat=True)
    )

    perfiles = Perfil.objects.select_related('user', 'usuario').filter(
        usuario__username__isnull=True,
    )

    for perfil in perfiles:
        base_username = perfil.user.username
        username = base_username
        suffix = 2
        while username in used_usernames:
            username = f'{base_username}{suffix}'
            suffix += 1

        perfil.usuario.username = username
        perfil.usuario.save(update_fields=['username'])
        used_usernames.add(username)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_categorias_iniciales'),
    ]

    operations = [
        migrations.RunPython(backfill_usuario_username, noop_reverse),
    ]
