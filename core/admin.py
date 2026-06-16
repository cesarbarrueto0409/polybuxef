from django.contrib import admin

from core.models import (
    Categoria,
    HistorialPrecio,
    Mercado,
    Opcion,
    Perfil,
    Resolucion,
    TransaccionShare,
    Usuario,
    Coleccionable,
    UsuarioColeccionable,
    RuletaProbabilidad,
    ConfiguracionRuleta,
    HistorialRuleta,
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


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo Usuario.
    """
    list_display = ['id', 'username', 'nombre', 'email', 'saldo', 'giros_disponibles', 'fecha_registro']
    search_fields = ['username', 'nombre', 'email']
    ordering = ['-fecha_registro']


@admin.register(TransaccionShare)
class TransaccionShareAdmin(admin.ModelAdmin):
    list_display = ["id", "usuario", "opcion", "tipo", "shares", "monto", "fecha"]
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


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "usuario"]
    search_fields = ["user__username", "usuario__nombre", "usuario__email"]



# ============================================================================
# ADMINISTRACIÓN DE COLECCIONABLES Y RULETA
# ============================================================================


@admin.register(Coleccionable)
class ColeccionableAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo Coleccionable.
    """
    list_display = ['id', 'nombre', 'rareza', 'fecha_creacion', 'total_propietarios']
    list_filter = ['rareza', 'fecha_creacion']
    search_fields = ['nombre', 'descripcion']
    ordering = ['rareza', 'nombre']


@admin.register(UsuarioColeccionable)
class UsuarioColeccionableAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo UsuarioColeccionable.
    """
    list_display = ['id', 'usuario', 'coleccionable', 'cantidad', 'fecha_obtencion']
    list_filter = ['coleccionable__rareza', 'fecha_obtencion']
    search_fields = ['usuario__nombre', 'coleccionable__nombre']
    ordering = ['-fecha_obtencion']
    raw_id_fields = ['usuario', 'coleccionable']


@admin.register(RuletaProbabilidad)
class RuletaProbabilidadAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo RuletaProbabilidad.
    """
    list_display = ['coleccionable', 'probabilidad', 'activo']
    list_filter = ['activo', 'coleccionable__rareza']
    search_fields = ['coleccionable__nombre']
    ordering = ['-probabilidad']


@admin.register(ConfiguracionRuleta)
class ConfiguracionRuletaAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo ConfiguracionRuleta.
    """
    list_display = ['id', 'costo_giro', 'activa', 'fecha_actualizacion']
    
    def has_add_permission(self, request):
        # Solo permitir un registro de configuración
        return not ConfiguracionRuleta.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # No permitir eliminar la configuración
        return False


@admin.register(HistorialRuleta)
class HistorialRuletaAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo HistorialRuleta.
    """
    list_display = ['id', 'usuario', 'coleccionable_obtenido', 'costo', 'fecha']
    list_filter = ['fecha', 'coleccionable_obtenido__rareza']
    search_fields = ['usuario__nombre', 'coleccionable_obtenido__nombre']
    ordering = ['-fecha']
    raw_id_fields = ['usuario', 'coleccionable_obtenido']
    
    def has_add_permission(self, request):
        # No permitir crear registros manualmente
        return False
    
    def has_change_permission(self, request, obj=None):
        # No permitir editar registros históricos
        return False
