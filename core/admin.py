from django.contrib import admin
from core.models import Categoria, Mercado, Opcion


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
