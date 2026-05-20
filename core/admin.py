from django.contrib import admin
from core.models import (
    Categoria, 
    Mercado, 
    Opcion, 
    Usuario, 
    TransaccionShare, 
    HistorialPrecio, 
    Resolucion
)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo Categoria.
    """
    list_display = ['id', 'nombre', 'contar_mercados']
    search_fields = ['nombre']
    ordering = ['nombre']


@admin.register(Mercado)
class MercadoAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo Mercado.
    """
    list_display = ['id', 'titulo', 'categoria', 'estado', 'fecha_creacion', 'fecha_cierre']
    list_filter = ['estado', 'categoria', 'fecha_creacion']
    search_fields = ['titulo', 'descripcion']
    ordering = ['-fecha_creacion']
    date_hierarchy = 'fecha_creacion'


@admin.register(Opcion)
class OpcionAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo Opcion.
    """
    list_display = ['id', 'nombre', 'mercado', 'tokens', 'precio', 'es_ganadora']
    list_filter = ['es_ganadora', 'mercado__estado']
    search_fields = ['nombre', 'mercado__titulo']
    ordering = ['-tokens']


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo Usuario.
    """
    list_display = ['id', 'nombre', 'email', 'saldo', 'fecha_registro']
    search_fields = ['nombre', 'email']
    ordering = ['-fecha_registro']


@admin.register(TransaccionShare)
class TransaccionShareAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo TransaccionShare.
    """
    list_display = ['id', 'id_usuario', 'id_opcion', 'tipo', 'shares', 'monto', 'fecha']
    list_filter = ['tipo', 'fecha']
    ordering = ['-fecha']


@admin.register(HistorialPrecio)
class HistorialPrecioAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo HistorialPrecio.
    """
    list_display = ['id', 'id_opcion', 'precio', 'fecha']
    list_filter = ['fecha']
    ordering = ['-fecha']


@admin.register(Resolucion)
class ResolucionAdmin(admin.ModelAdmin):
    """
    Configuración del admin para el modelo Resolucion.
    """
    list_display = ['id', 'id_mercado', 'id_opcion_ganadora', 'fecha']
    ordering = ['-fecha']
