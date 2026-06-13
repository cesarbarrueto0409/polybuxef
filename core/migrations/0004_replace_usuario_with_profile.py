# reemplaza el sistema Usuario/Perfil por Profile/Transaction
# y actualiza TransaccionShare para usar Profile

#   Crea Profile
#   Crea Transaction
#   Migra TransaccionShare para usar Profile y no Usuario
#   Elimina perfil y usuario

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_merge_0002_perfil_0002_usuario_day_streak"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # profile
        migrations.CreateModel(
            name="Profile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("nombre", models.CharField(default="", max_length=100)),
                ("racha_actual", models.PositiveIntegerField(default=0)),
                ("ultima_racha", models.DateField(blank=True, null=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        # transaction
        migrations.CreateModel(
            name="Transaction",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "kind",
                    models.CharField(
                        choices=[("IN", "Ingreso"), ("OUT", "Egreso")], max_length=3
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("BET_BUY", "Compra de shares"),
                            ("BET_SELL", "Venta de shares"),
                            ("BET_REWARD", "Recompensa de apuesta"),
                            ("STREAK_REWARD", "Recompensa diaria"),
                            ("ADMIN_GRANT", "Saldo otorgado por administrador"),
                            ("ADMIN_REMOVE", "Saldo removido por administrador"),
                        ],
                        max_length=20,
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("reverted", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="transactions",
                        to="core.profile",
                    ),
                ),
            ],
        ),
        # agregar  profile_id a TransaccionShare
        migrations.AddField(
            model_name="transaccionshare",
            name="profile",
            field=models.ForeignKey(
                null=True,          # nullable temporalmente para la migración de datos
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="transacciones_shares",
                to="core.profile",
            ),
        ),
        # quitar usuario de TransaccionShare
        migrations.RemoveField(
            model_name="transaccionshare",
            name="usuario",
        ),
        # hacer profile NOT NULL
        migrations.AlterField(
            model_name="transaccionshare",
            name="profile",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="transacciones_shares",
                to="core.profile",
            ),
        ),
        # corregir max_digits de precio_unitario a 18
        migrations.AlterField(
            model_name="transaccionshare",
            name="precio_unitario",
            field=models.DecimalField(decimal_places=6, max_digits=18),
        ),
        # actualizar índices de TransaccionShare
        migrations.RemoveIndex(
            model_name="transaccionshare",
            name="transaccion_usuario_3ebdc2_idx",
        ),
        migrations.AddIndex(
            model_name="transaccionshare",
            index=models.Index(
                fields=["profile", "opcion"],
                name="transaccion_profile_opcion_idx",
            ),
        ),
        # eliminar Perfil y Usuario
        migrations.DeleteModel(
            name="Perfil",
        ),
        migrations.DeleteModel(
            name="Usuario",
        ),
    ]
