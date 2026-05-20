from django.contrib import admin

from core.models import (
    Categoria,
    HistorialPrecio,
    Mercado,
    Opcion,
    Profile,
    Resolucion,
    Transaction,
    TransaccionShare,
)

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ["id", "nombre", "contar_mercados"]
    search_fields = ["nombre"]
    ordering = ["nombre"]


@admin.register(Mercado)
class MercadoAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "titulo",
        "categoria",
        "estado",
        "liquidez_total",
        "fecha_creacion",
        "fecha_cierre",
    ]
    list_filter = ["estado", "categoria", "fecha_creacion"]
    search_fields = ["titulo", "descripcion"]
    ordering = ["-fecha_creacion"]
    date_hierarchy = "fecha_creacion"


@admin.register(Opcion)
class OpcionAdmin(admin.ModelAdmin):
    list_display = ["id", "nombre", "mercado", "tokens", "precio", "es_ganadora"]
    list_filter = ["es_ganadora", "mercado__estado"]
    search_fields = ["nombre", "mercado__titulo"]
    ordering = ["-tokens"]


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "nombre", "racha_actual", "ultima_racha"]
    search_fields = ["user__username", "nombre"]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["id", "profile", "kind", "category", "amount", "reverted", "created_at"]
    list_filter = ["kind", "category", "reverted"]
    ordering = ["-created_at"]


@admin.register(TransaccionShare)
class TransaccionShareAdmin(admin.ModelAdmin):
    list_display = ["id", "profile", "opcion", "tipo", "shares", "monto", "fecha"]
    list_filter = ["tipo", "fecha"]
    ordering = ["-fecha"]


@admin.register(HistorialPrecio)
class HistorialPrecioAdmin(admin.ModelAdmin):
    list_display = ["id", "opcion", "precio", "fecha"]
    list_filter = ["fecha"]
    ordering = ["-fecha"]


@admin.register(Resolucion)
class ResolucionAdmin(admin.ModelAdmin):
    list_display = ["id", "mercado", "opcion_ganadora", "fecha"]
    ordering = ["-fecha"]
