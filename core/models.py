from django.db import models

# Create your models here.
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User


# corri esos comandos
# python manage.py makemigrations
# python manage.py migrate


class Usuario(models.Model):
  nombre = models.CharField(max_length=100)
  email = models.EmailField(max_length=150, unique=True)
  saldo = models.DecimalField(max_digits=18, decimal_places=2, default=0,
                              validators=[MinValueValidator(0)])
  fecha_registro = models.DateTimeField(auto_now_add=True)

  class Meta:
    db_table = 'usuarios'


class Categoria(models.Model):
  nombre = models.CharField(max_length=100, unique=True)

  class Meta:
    db_table = 'categorias'


class Mercado(models.Model):
  ESTADO_CHOICES = [('abierto','Abierto'), ('cerrado','Cerrado'),
                    ('resuelto','Resuelto'), ('cancelado','Cancelado')]

  categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT)
  titulo = models.CharField(max_length=255)
  descripcion = models.TextField(blank=True, null=True)
  imagen_url = models.CharField(max_length=255, blank=True, null=True)
  estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='abierto')
  liquidez_total = models.DecimalField(max_digits=18, decimal_places=2, default=0)
  fecha_cierre = models.DateTimeField()
  fecha_creacion = models.DateTimeField(auto_now_add=True)

  class Meta:
    db_table = 'mercados'
    indexes = [models.Index(fields=['estado', 'fecha_cierre'])]


class Opcion(models.Model):
  mercado = models.ForeignKey(Mercado, on_delete=models.CASCADE, related_name='opciones')
  nombre = models.CharField(max_length=100)
  tokens = models.DecimalField(max_digits=18, decimal_places=6, default=1000)
  precio = models.DecimalField(max_digits=7, decimal_places=6, default=0.5,
                                validators=[MinValueValidator(0), MaxValueValidator(1)])
  es_ganadora = models.BooleanField(null=True, default=None)

  class Meta:
    db_table = 'opciones'
    indexes = [models.Index(fields=['mercado'])]


class TransaccionShare(models.Model):
  TIPO_CHOICES = [('compra','Compra'), ('venta','Venta'), ('redencion','Redención')]

  usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT)
  opcion = models.ForeignKey(Opcion, on_delete=models.PROTECT)
  tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
  shares = models.DecimalField(max_digits=18, decimal_places=6)
  monto = models.DecimalField(max_digits=18, decimal_places=2)
  precio_unitario = models.DecimalField(max_digits=7, decimal_places=6)
  fecha = models.DateTimeField(auto_now_add=True)

  class Meta:
    db_table = 'transacciones_shares'
    indexes = [
        models.Index(fields=['usuario', 'opcion']),
        models.Index(fields=['opcion']),
    ]


class HistorialPrecio(models.Model):
  opcion = models.ForeignKey(Opcion, on_delete=models.CASCADE)
  precio = models.DecimalField(max_digits=7, decimal_places=6)
  fecha = models.DateTimeField(auto_now_add=True)

  class Meta:
    db_table = 'historial_precios'
    indexes = [models.Index(fields=['opcion', 'fecha'])]


class Resolucion(models.Model):
  mercado = models.OneToOneField(Mercado, on_delete=models.PROTECT)
  opcion_ganadora = models.ForeignKey(Opcion, on_delete=models.PROTECT)
  fecha = models.DateTimeField(auto_now_add=True)

  class Meta:
    db_table = 'resoluciones'


class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE)

    class Meta:
        db_table = 'perfiles'