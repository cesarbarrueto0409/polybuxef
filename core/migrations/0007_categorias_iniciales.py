from django.db import migrations

CATEGORIAS = [
    "Deportes",
    "Política",
    "Tecnología",
    "Entretenimiento",
    "Ciencia",
    "Economía",
    "Universidad",
    "Otros",
]


def agregar_categorias(apps, schema_editor):
    Categoria = apps.get_model("core", "Categoria")
    for nombre in CATEGORIAS:
        Categoria.objects.get_or_create(nombre=nombre)


def eliminar_categorias(apps, schema_editor):
    Categoria = apps.get_model("core", "Categoria")
    Categoria.objects.filter(nombre__in=CATEGORIAS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_propuestamercado"),
    ]

    operations = [
        migrations.RunPython(agregar_categorias, eliminar_categorias),
    ]