from django.contrib import admin

# Register your models here.
# core/admin.py
from django.contrib import admin
from .models import Usuario, Categoria, Mercado, Opcion, TransaccionShare, HistorialPrecio, Resolucion

admin.site.register(Usuario)
admin.site.register(Categoria)
admin.site.register(Mercado)
admin.site.register(Opcion)
admin.site.register(TransaccionShare)
admin.site.register(HistorialPrecio)
admin.site.register(Resolucion)