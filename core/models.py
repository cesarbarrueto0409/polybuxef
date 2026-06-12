from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Usuario(models.Model):
    username = models.CharField(
        max_length=50,
        unique=True,
        null=True,  # Temporal para la migración
        blank=True,
        help_text="Nombre de usuario único (ej: cesar.hola)"
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
    # Campos para sistema de ruleta
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
        """
        Verifica si el usuario tiene saldo suficiente.
        
        Args:
            monto (Decimal): Monto a verificar
        
        Returns:
            bool: True si tiene saldo suficiente
        """
        return self.saldo >= monto
    
    def descontar_saldo(self, monto):
        """
        Descuenta saldo del usuario.
        
        Args:
            monto (Decimal): Monto a descontar
        
        Raises:
            ValueError: Si no tiene saldo suficiente
        """
        if not self.tiene_saldo_suficiente(monto):
            raise ValueError("Saldo insuficiente")
        
        self.saldo -= monto
        self.save(update_fields=['saldo'])
    
    def agregar_giros(self, cantidad):
        """
        Agrega giros disponibles al usuario.
        
        Args:
            cantidad (int): Cantidad de giros a agregar
        """
        self.giros_disponibles += cantidad
        self.save(update_fields=['giros_disponibles'])
    
    def tiene_giros_disponibles(self):
        """
        Verifica si el usuario tiene giros disponibles.
        
        Returns:
            bool: True si tiene giros disponibles
        """
        return self.giros_disponibles > 0
    
    def descontar_giro(self):
        """
        Descuenta un giro del usuario.
        
        Raises:
            ValueError: Si no tiene giros disponibles
        """
        if not self.tiene_giros_disponibles():
            raise ValueError("No tienes giros disponibles")
        
        self.giros_disponibles -= 1
        self.ultima_ruleta = timezone.now()
        self.save(update_fields=['giros_disponibles', 'ultima_ruleta'])


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


# ============================================================================
# SISTEMA DE COLECCIONABLES Y RULETA
# ============================================================================


class Coleccionable(models.Model):
    """
    Catálogo global de coleccionables disponibles en el sistema.
    
    Define todos los coleccionables que existen y pueden ser obtenidos
    por los usuarios a través de la ruleta.
    """
    RAREZA_CHOICES = [
        ('comun', 'Común'),
        ('raro', 'Raro'),
        ('epico', 'Épico'),
        ('legendario', 'Legendario'),
    ]
    
    nombre = models.CharField(
        max_length=100,
        unique=True,
        help_text="Nombre del coleccionable"
    )
    descripcion = models.TextField(
        blank=True,
        help_text="Descripción del coleccionable"
    )
    imagen_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="URL de la imagen del coleccionable"
    )
    rareza = models.CharField(
        max_length=15,
        choices=RAREZA_CHOICES,
        default='comun',
        help_text="Nivel de rareza del coleccionable"
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha de creación del coleccionable"
    )
    
    class Meta:
        db_table = "coleccionables"
        verbose_name = "Coleccionable"
        verbose_name_plural = "Coleccionables"
        ordering = ['rareza', 'nombre']
    
    def __str__(self):
        return f"{self.nombre} ({self.get_rareza_display()})"
    
    def total_propietarios(self):
        """
        Cuenta cuántos usuarios tienen este coleccionable.
        
        Returns:
            int: Cantidad de usuarios que lo poseen
        """
        return self.propietarios.count()


class UsuarioColeccionable(models.Model):
    """
    Relación entre usuarios y coleccionables (inventario personal).
    
    Tabla intermedia que registra qué coleccionables posee cada usuario,
    cuántas veces lo ha obtenido y cuándo lo obtuvo por primera vez.
    """
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='coleccionables_obtenidos',
        help_text="Usuario propietario"
    )
    coleccionable = models.ForeignKey(
        Coleccionable,
        on_delete=models.CASCADE,
        related_name='propietarios',
        help_text="Coleccionable obtenido"
    )
    cantidad = models.PositiveIntegerField(
        default=1,
        help_text="Cantidad de veces que ha obtenido este coleccionable"
    )
    fecha_obtencion = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha en que obtuvo el coleccionable por primera vez"
    )
    fecha_ultima_obtencion = models.DateTimeField(
        auto_now=True,
        help_text="Fecha de la última vez que obtuvo este coleccionable"
    )
    
    class Meta:
        db_table = "usuario_coleccionables"
        verbose_name = "Coleccionable de Usuario"
        verbose_name_plural = "Coleccionables de Usuarios"
        unique_together = ['usuario', 'coleccionable']
        ordering = ['-fecha_obtencion']
    
    def __str__(self):
        return f"{self.usuario.nombre} - {self.coleccionable.nombre} (x{self.cantidad})"
    
    def incrementar_cantidad(self):
        """
        Incrementa la cantidad cuando el usuario obtiene el mismo coleccionable nuevamente.
        """
        self.cantidad += 1
        self.save(update_fields=['cantidad', 'fecha_ultima_obtencion'])


class RuletaProbabilidad(models.Model):
    """
    Configuración de probabilidades para la ruleta.
    
    Define la probabilidad de obtener cada coleccionable al girar la ruleta
    y si está activo o no en el sistema.
    """
    coleccionable = models.OneToOneField(
        Coleccionable,
        on_delete=models.CASCADE,
        related_name='probabilidad_ruleta',
        help_text="Coleccionable al que aplica la probabilidad"
    )
    probabilidad = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001')), MaxValueValidator(Decimal('1.0000'))],
        help_text="Probabilidad de obtenerlo (entre 0.0001 y 1.0000)"
    )
    activo = models.BooleanField(
        default=True,
        help_text="Si está disponible en la ruleta actualmente"
    )
    
    class Meta:
        db_table = "ruleta_probabilidades"
        verbose_name = "Probabilidad de Ruleta"
        verbose_name_plural = "Probabilidades de Ruleta"
        ordering = ['-probabilidad']
    
    def __str__(self):
        estado = "Activo" if self.activo else "Inactivo"
        return f"{self.coleccionable.nombre}: {float(self.probabilidad)*100:.2f}% ({estado})"


class ConfiguracionRuleta(models.Model):
    """
    Configuración global del sistema de ruleta.
    
    Define parámetros como el costo de un giro y otros ajustes generales.
    Solo debe existir un registro en esta tabla.
    """
    costo_giro = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('100.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Costo en saldo para comprar un giro"
    )
    activa = models.BooleanField(
        default=True,
        help_text="Si la ruleta está activa en el sistema"
    )
    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
        help_text="Última actualización de la configuración"
    )
    
    class Meta:
        db_table = "configuracion_ruleta"
        verbose_name = "Configuración de Ruleta"
        verbose_name_plural = "Configuración de Ruleta"
    
    def __str__(self):
        estado = "Activa" if self.activa else "Inactiva"
        return f"Ruleta: ${self.costo_giro} por giro ({estado})"
    
    def save(self, *args, **kwargs):
        """
        Asegura que solo exista un registro de configuración.
        """
        if not self.pk and ConfiguracionRuleta.objects.exists():
            raise ValueError("Solo puede existir una configuración de ruleta")
        return super().save(*args, **kwargs)
    
    @classmethod
    def obtener_configuracion(cls):
        """
        Obtiene la configuración actual de la ruleta.
        Crea una por defecto si no existe.
        
        Returns:
            ConfiguracionRuleta: Configuración actual
        """
        config, created = cls.objects.get_or_create(pk=1)
        return config


class HistorialRuleta(models.Model):
    """
    Registro histórico de giros de ruleta.
    
    Mantiene un historial completo de cada vez que un usuario gira la ruleta,
    qué obtuvo y cuánto pagó.
    """
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='historial_ruletas',
        help_text="Usuario que giró la ruleta"
    )
    coleccionable_obtenido = models.ForeignKey(
        Coleccionable,
        on_delete=models.PROTECT,
        related_name='historial_obtencion',
        help_text="Coleccionable que obtuvo"
    )
    costo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Costo que pagó por el giro"
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora del giro"
    )
    
    class Meta:
        db_table = "historial_ruletas"
        verbose_name = "Historial de Ruleta"
        verbose_name_plural = "Historial de Ruletas"
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['usuario', '-fecha']),
            models.Index(fields=['coleccionable_obtenido']),
        ]
    
    def __str__(self):
        return f"{self.usuario.nombre} obtuvo {self.coleccionable_obtenido.nombre} el {self.fecha.strftime('%Y-%m-%d %H:%M')}"
