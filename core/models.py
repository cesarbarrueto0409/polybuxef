from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Usuario(models.Model):
    nombre = models.CharField(max_length=100)
    email = models.EmailField(max_length=150, unique=True)
    saldo = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    racha_actual = models.PositiveIntegerField(default=0)
    ultima_racha = models.DateField(blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "usuarios"

    def __str__(self):
        return self.nombre


class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "categorias"

    def __str__(self):
        return self.nombre

    def get_mercados_activos(self):
        return self.mercado_set.filter(estado="abierto")

    def contar_mercados(self):
        return self.mercado_set.count()


class Mercado(models.Model):
    ESTADO_CHOICES = [
        ("abierto", "Abierto"),
        ("cerrado", "Cerrado"),
        ("resuelto", "Resuelto"),
        ("cancelado", "Cancelado"),
    ]

    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT)
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, null=True)
    imagen_url = models.CharField(max_length=255, blank=True, null=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default="abierto")
    liquidez_total = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    fecha_cierre = models.DateTimeField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mercados"
        indexes = [models.Index(fields=["estado", "fecha_cierre"])]

    def __str__(self):
        return f"{self.titulo} ({self.estado})"

    def get_opciones(self):
        return self.opciones.all()

    def cerrar_mercado(self):
        self.estado = "cerrado"
        self.save(update_fields=["estado"])

    def cancelar_mercado(self):
        self.estado = "cancelado"
        self.save(update_fields=["estado"])

    def esta_abierto(self):
        return self.estado == "abierto"

    def calcular_total_tokens(self):
        return self.opciones.aggregate(total=models.Sum("tokens"))["total"] or Decimal("0")


class Opcion(models.Model):
    mercado = models.ForeignKey(Mercado, on_delete=models.CASCADE, related_name="opciones")
    nombre = models.CharField(max_length=100)
    tokens = models.DecimalField(max_digits=18, decimal_places=6, default=1000)
    precio = models.DecimalField(
        max_digits=7,
        decimal_places=6,
        default=0.5,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    es_ganadora = models.BooleanField(null=True, default=None)

    class Meta:
        db_table = "opciones"
        indexes = [models.Index(fields=["mercado"])]

    def __str__(self):
        return f"{self.nombre} - {self.mercado.titulo}"

    def agregar_tokens(self, cantidad):
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor a 0")
        self.tokens += cantidad
        self.save(update_fields=["tokens"])

    def quitar_tokens(self, cantidad):
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor a 0")
        if cantidad > self.tokens:
            raise ValueError("No hay suficientes tokens para quitar")
        self.tokens -= cantidad
        self.save(update_fields=["tokens"])

    def actualizar_precio(self, nuevo_precio):
        if nuevo_precio < 0 or nuevo_precio > 1:
            raise ValueError("El precio debe estar entre 0 y 1")
        self.precio = nuevo_precio
        self.save(update_fields=["precio"])

    def marcar_como_ganadora(self):
        self.es_ganadora = True
        self.save(update_fields=["es_ganadora"])

    def calcular_probabilidad(self):
        total_tokens = self.mercado.calcular_total_tokens()
        if total_tokens == 0:
            return Decimal("0.00")
        return round((self.tokens / total_tokens) * 100, 2)


class TransaccionShare(models.Model):
    TIPO_CHOICES = [
        ("compra", "Compra"),
        ("venta", "Venta"),
        ("redencion", "Redención"),
    ]

    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    opcion = models.ForeignKey(Opcion, on_delete=models.PROTECT)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    shares = models.DecimalField(max_digits=18, decimal_places=6)
    monto = models.DecimalField(max_digits=18, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=7, decimal_places=6)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "transacciones_shares"
        indexes = [
            models.Index(fields=["usuario", "opcion"]),
            models.Index(fields=["opcion"]),
        ]

    def __str__(self):
        return f"{self.tipo} | {self.usuario} | {self.opcion}"


class HistorialPrecio(models.Model):
    opcion = models.ForeignKey(Opcion, on_delete=models.CASCADE)
    precio = models.DecimalField(max_digits=7, decimal_places=6)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "historial_precios"
        indexes = [models.Index(fields=["opcion", "fecha"])]

    def __str__(self):
        return f"{self.opcion} | {self.precio}"


class Resolucion(models.Model):
    mercado = models.OneToOneField(Mercado, on_delete=models.PROTECT)
    opcion_ganadora = models.ForeignKey(Opcion, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "resoluciones"

    def __str__(self):
        return f"{self.mercado} -> {self.opcion_ganadora}"


class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE)

    class Meta:
        db_table = "perfiles"

    def __str__(self):
        return f"Perfil de {self.user.username}"
