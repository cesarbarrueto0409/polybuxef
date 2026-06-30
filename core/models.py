"""
Modelos del sistema PolyBuxef.

Define todas las entidades de la aplicación: usuarios, mercados, opciones,
transacciones, coleccionables y configuración de la ruleta.
"""
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Usuario(models.Model):
    """
    Modelo principal de usuario de la plataforma.
    
    Almacena información de perfil, saldo, racha diaria y datos de la ruleta.
    """
    username = models.CharField(
        max_length=50,
        unique=True,
        help_text="Nombre de usuario único (ej: user.test)"
    )
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
    giros_disponibles = models.PositiveIntegerField(
        default=0,
        help_text="Cantidad de giros disponibles para la ruleta"
    )
    ultima_ruleta = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Última vez que giró la ruleta"
    )

    class Meta:
        db_table = "usuarios"

    def __str__(self):
        return f"@{self.username} ({self.nombre})"
    
    def tiene_saldo_suficiente(self, monto):
        """Verifica si el usuario tiene saldo suficiente."""
        return self.saldo >= monto
    
    def descontar_saldo(self, monto):
        """Descuenta saldo del usuario."""
        if not self.tiene_saldo_suficiente(monto):
            raise ValueError("Saldo insuficiente")
        self.saldo -= monto
        self.save(update_fields=['saldo'])
    
    def agregar_giros(self, cantidad):
        """Agrega giros disponibles al usuario."""
        self.giros_disponibles += cantidad
        self.save(update_fields=['giros_disponibles'])
    
    def tiene_giros_disponibles(self):
        """Verifica si el usuario tiene giros disponibles."""
        return self.giros_disponibles > 0
    
    def descontar_giro(self):
        """Descuenta un giro del usuario."""
        if not self.tiene_giros_disponibles():
            raise ValueError("No tienes giros disponibles")
        self.giros_disponibles -= 1
        self.ultima_ruleta = timezone.now()
        self.save(update_fields=['giros_disponibles', 'ultima_ruleta'])


class Perfil(models.Model):
    """
    Tabla intermedia entre User de Django y Usuario de la plataforma.
    
    Permite vincular las cuentas de autenticación con los perfiles
    internos que manejan saldo, apuestas y coleccionables.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE)

    class Meta:
        db_table = "perfiles"

    def __str__(self):
        return f"Perfil de {self.user.username}"


class Categoria(models.Model):
    """Categoría de mercados de apuestas."""
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
    """Mercado de apuestas sobre un evento."""
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
    """Opción de apuesta dentro de un mercado."""
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
    """Transacción de compra/venta de shares en opciones."""
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
    precio_unitario = models.DecimalField(max_digits=18, decimal_places=6)
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
    """Registro histórico de precios de opciones."""
    opcion = models.ForeignKey(Opcion, on_delete=models.CASCADE)
    precio = models.DecimalField(max_digits=7, decimal_places=6)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "historial_precios"
        indexes = [models.Index(fields=["opcion", "fecha"])]

    def __str__(self):
        return f"{self.opcion} | {self.precio}"


class Resolucion(models.Model):
    """Resolución de un mercado con la opción ganadora."""
    mercado = models.OneToOneField(Mercado, on_delete=models.PROTECT)
    opcion_ganadora = models.ForeignKey(Opcion, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "resoluciones"

    def __str__(self):
        return f"{self.mercado} -> {self.opcion_ganadora}"


# ============================================================================
# SISTEMA DE COLECCIONABLES Y RULETA
# ============================================================================


class Coleccionable(models.Model):
    """Catálogo global de coleccionables disponibles en el sistema."""
    RAREZA_CHOICES = [
        ('comun', 'Común'),
        ('raro', 'Raro'),
        ('epico', 'Épico'),
        ('legendario', 'Legendario'),
    ]
    
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    imagen_url = models.URLField(max_length=500, blank=True, null=True)
    rareza = models.CharField(max_length=15, choices=RAREZA_CHOICES, default='comun')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "coleccionables"
        verbose_name = "Coleccionable"
        verbose_name_plural = "Coleccionables"
        ordering = ['rareza', 'nombre']
    
    def __str__(self):
        return f"{self.nombre} ({self.get_rareza_display()})"
    
    def total_propietarios(self):
        return self.propietarios.count()


class UsuarioColeccionable(models.Model):
    """Inventario personal de coleccionables del usuario."""
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='coleccionables_obtenidos')
    coleccionable = models.ForeignKey(Coleccionable, on_delete=models.CASCADE, related_name='propietarios')
    cantidad = models.PositiveIntegerField(default=1)
    fecha_obtencion = models.DateTimeField(auto_now_add=True)
    fecha_ultima_obtencion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "usuario_coleccionables"
        unique_together = ['usuario', 'coleccionable']
        ordering = ['-fecha_obtencion']
    
    def __str__(self):
        return f"{self.usuario.nombre} - {self.coleccionable.nombre} (x{self.cantidad})"
    
    def incrementar_cantidad(self):
        self.cantidad += 1
        self.save(update_fields=['cantidad', 'fecha_ultima_obtencion'])


class RuletaProbabilidad(models.Model):
    """Configuración de probabilidades para la ruleta."""
    coleccionable = models.OneToOneField(Coleccionable, on_delete=models.CASCADE, related_name='probabilidad_ruleta')
    probabilidad = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001')), MaxValueValidator(Decimal('1.0000'))]
    )
    activo = models.BooleanField(default=True)
    
    class Meta:
        db_table = "ruleta_probabilidades"
        ordering = ['-probabilidad']
    
    def __str__(self):
        estado = "Activo" if self.activo else "Inactivo"
        return f"{self.coleccionable.nombre}: {float(self.probabilidad)*100:.2f}% ({estado})"


class ConfiguracionRuleta(models.Model):
    """Configuración global del sistema de ruleta."""
    costo_giro = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('100.00'),
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    activa = models.BooleanField(default=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "configuracion_ruleta"
    
    def __str__(self):
        estado = "Activa" if self.activa else "Inactiva"
        return f"Ruleta: ${self.costo_giro} por giro ({estado})"
    
    def save(self, *args, **kwargs):
        if not self.pk and ConfiguracionRuleta.objects.exists():
            raise ValueError("Solo puede existir una configuración de ruleta")
        return super().save(*args, **kwargs)
    
    @classmethod
    def obtener_configuracion(cls):
        config, created = cls.objects.get_or_create(pk=1)
        return config


class HistorialRuleta(models.Model):
    """Registro histórico de giros de ruleta."""
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='historial_ruletas')
    coleccionable_obtenido = models.ForeignKey(Coleccionable, on_delete=models.PROTECT, related_name='historial_obtencion')
    costo = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "historial_ruletas"
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['usuario', '-fecha']),
            models.Index(fields=['coleccionable_obtenido']),
        ]
    
    def __str__(self):
        return f"{self.usuario.nombre} obtuvo {self.coleccionable_obtenido.nombre} el {self.fecha.strftime('%Y-%m-%d %H:%M')}"

class PropuestaMercado(models.Model):
    """
    Propuesta de mercado enviada por un usuario normal.
    Un admin debe aprobarla para que se convierta en un Mercado real.
    """
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
    ]

    usuario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name='propuestas'
    )
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField()
    categoria = models.ForeignKey(
        Categoria, on_delete=models.SET_NULL, null=True, blank=True
    )
    fecha_cierre_propuesta = models.DateTimeField(
        help_text="Fecha en que el usuario sugiere cerrar el mercado"
    )
    estado = models.CharField(
        max_length=10, choices=ESTADO_CHOICES, default='pendiente'
    )
    motivo_rechazo = models.TextField(
        blank=True,
        help_text="Razón por la que se rechazó la propuesta (opcional)"
    )
    mercado_creado = models.OneToOneField(
        Mercado, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='propuesta_origen',
        help_text="Mercado que se creó al aprobar esta propuesta"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'propuestas_mercado'
        ordering = ['-fecha_creacion']
        verbose_name = 'Propuesta de Mercado'
        verbose_name_plural = 'Propuestas de Mercado'

    def __str__(self):
        return f"[{self.get_estado_display()}] {self.titulo} — @{self.usuario.username}"
