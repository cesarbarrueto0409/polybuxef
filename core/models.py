from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum
from decimal import Decimal


class Profile(models.Model):
    """
    Perfil de usuario del sistema.

    Relación 1 a 1 con el usuario de Django.
    Calcula el saldo del usuario a partir de sus transacciones (ledger system).
    Permite acceso al historial de transacciones del usuario.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def get_balance(self) -> Decimal:
        """
        Calcula el saldo actual del usuario
        sumando ingresos y egresos.

        Returns:
            Decimal: saldo actual del usuario
        """
        income = self.transactions.filter(kind="IN").aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")

        expenses = self.transactions.filter(kind="OUT").aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")

        return income - expenses

    def get_transaction_history(self):
        """
        Obtiene el historial de transacciones del usuario
        ordenado desde la más reciente a la más antigua.

        Returns:
            QuerySet[Transaction]: historial de transacciones
        """
        return self.transactions.order_by("-created_at")


class Transaction(models.Model):
    """
    Registro de transacciones del sistema (ledger).

    Representa movimientos de dinero asociados a un usuario,
    permitiendo mantener historial financiero y trazabilidad
    de operaciones dentro de la plataforma. Además, permite
    revertir transacciones, anulando abonos/cargos y
    registrando la acción.

    Cada transacción posee:

        Tipos de movimiento: (kind)
        - IN: ingreso de dinero
        - OUT: salida de dinero

        Categorías: (category)
        - BET_BUY
        - BET_SELL
        - BET_REWARD
        - STREAK_REWARD
        - ADMIN_GRANT
        - ADMIN_REMOVE

    """

    KIND_CHOICES = [
        ("IN", "Ingreso"),
        ("OUT", "Egreso"),
    ]

    CATEGORY_CHOICES = [
        ("BET_BUY", "Compra de shares"),
        ("BET_SELL", "Venta de shares"),
        ("BET_REWARD", "Recompensa de apuesta"),
        ("STREAK_REWARD", "Recompensa diaria"),
        ("ADMIN_GRANT", "Saldo otorgado por administrador"),
        ("ADMIN_REMOVE", "Saldo removido por administrador"),
    ]

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="transactions"
    )

    kind = models.CharField(
        max_length=3,
        choices=KIND_CHOICES
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    description = models.CharField(
        max_length=255,
        blank=True
    )

    reverted = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.kind} | {self.category} | {self.amount}"
from django.core.validators import MinValueValidator
from decimal import Decimal


class Categoria(models.Model):
    """
    Categoría de mercados de apuestas.
    
    Agrupa mercados relacionados por temática
    (ej: deportes, política universitaria, eventos académicos).
    """
    nombre = models.CharField(
        max_length=100,
        unique=True,
        help_text="Nombre de la categoría"
    )
    
    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre
    
    def get_mercados_activos(self):
        """
        Obtiene todos los mercados activos de esta categoría.
        
        Returns:
            QuerySet[Mercado]: mercados con estado 'abierto'
        """
        return self.mercados.filter(estado='abierto')
    
    def contar_mercados(self):
        """
        Cuenta el total de mercados en esta categoría.
        
        Returns:
            int: cantidad de mercados
        """
        return self.mercados.count()


class Mercado(models.Model):
    """
    Mercado de apuestas.
    
    Representa un evento sobre el cual los usuarios pueden apostar.
    Contiene múltiples opciones de apuesta y gestiona su ciclo de vida
    (abierto, cerrado, resuelto).
    """
    ESTADO_CHOICES = [
        ('abierto', 'Abierto'),
        ('cerrado', 'Cerrado'),
        ('resuelto', 'Resuelto'),
        ('cancelado', 'Cancelado'),
    ]
    
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.CASCADE,
        related_name='mercados',
        help_text="Categoría a la que pertenece el mercado"
    )
    titulo = models.CharField(
        max_length=255,
        help_text="Título del mercado"
    )
    descripcion = models.TextField(
        help_text="Descripción detallada del mercado"
    )
    imagen_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="URL de la imagen del mercado"
    )
    estado = models.CharField(
        max_length=10,
        choices=ESTADO_CHOICES,
        default='abierto',
        help_text="Estado actual del mercado"
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha de creación del mercado"
    )
    fecha_cierre = models.DateTimeField(
        help_text="Fecha límite para realizar apuestas"
    )
    
    class Meta:
        verbose_name = "Mercado"
        verbose_name_plural = "Mercados"
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.titulo} ({self.estado})"
    
    def get_opciones(self):
        """
        Obtiene todas las opciones de apuesta de este mercado.
        
        Returns:
            QuerySet[Opcion]: opciones del mercado
        """
        return self.opciones.all()
    
    def cerrar_mercado(self):
        """
        Cierra el mercado, impidiendo nuevas apuestas.
        """
        self.estado = 'cerrado'
        self.save()
    
    def cancelar_mercado(self):
        """
        Cancela el mercado.
        """
        self.estado = 'cancelado'
        self.save()
    
    def esta_abierto(self):
        """
        Verifica si el mercado está abierto para apuestas.
        
        Returns:
            bool: True si el mercado está abierto
        """
        return self.estado == 'abierto'
    
    def calcular_total_tokens(self):
        """
        Calcula el total de tokens apostados en todas las opciones.
        
        Returns:
            Decimal: suma total de tokens
        """
        total = self.opciones.aggregate(
            total=models.Sum('tokens')
        )['total'] or Decimal('0')
        return total


class Opcion(models.Model):
    """
    Opción de apuesta dentro de un mercado.
    
    Representa una posible respuesta o resultado del mercado.
    Los usuarios compran shares de opciones, y el precio se ajusta
    dinámicamente según la demanda (tokens apostados).
    """
    mercado = models.ForeignKey(
        Mercado,
        on_delete=models.CASCADE,
        related_name='opciones',
        help_text="Mercado al que pertenece la opción"
    )
    nombre = models.CharField(
        max_length=255,
        help_text="Nombre de la opción"
    )
    tokens = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total de tokens apostados en esta opción"
    )
    precio = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.5000'),
        validators=[MinValueValidator(Decimal('0.0001'))],
        help_text="Precio actual de la opción (probabilidad implícita)"
    )
    es_ganadora = models.BooleanField(
        default=False,
        help_text="Indica si esta opción ganó el mercado"
    )
    
    class Meta:
        verbose_name = "Opción"
        verbose_name_plural = "Opciones"
        ordering = ['-tokens']
    
    def __str__(self):
        return f"{self.nombre} - {self.mercado.titulo}"
    
    def agregar_tokens(self, cantidad):
        """
        Agrega tokens a la opción (cuando un usuario compra shares).
        
        Args:
            cantidad (Decimal): cantidad de tokens a agregar
        
        Raises:
            ValueError: si la cantidad es menor o igual a cero
        """
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor a 0")
        
        self.tokens += cantidad
        self.save()
    
    def quitar_tokens(self, cantidad):
        """
        Quita tokens de la opción (cuando un usuario vende shares).
        
        Args:
            cantidad (Decimal): cantidad de tokens a quitar
        
        Raises:
            ValueError: si la cantidad es inválida o excede los tokens disponibles
        """
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor a 0")
        
        if cantidad > self.tokens:
            raise ValueError("No hay suficientes tokens para quitar")
        
        self.tokens -= cantidad
        self.save()
    
    def actualizar_precio(self, nuevo_precio):
        """
        Actualiza el precio de la opción.
        
        Args:
            nuevo_precio (Decimal): nuevo precio de la opción
        
        Raises:
            ValueError: si el precio es inválido
        """
        if nuevo_precio <= 0 or nuevo_precio > 1:
            raise ValueError("El precio debe estar entre 0 y 1")
        
        self.precio = nuevo_precio
        self.save()
    
    def marcar_como_ganadora(self):
        """
        Marca esta opción como ganadora del mercado.
        """
        self.es_ganadora = True
        self.save()
    
    def calcular_probabilidad(self):
        """
        Calcula la probabilidad implícita basada en los tokens totales del mercado.
        
        Returns:
            Decimal: probabilidad como porcentaje (0-100)
        """
        total_tokens = self.mercado.calcular_total_tokens()
        
        if total_tokens == 0:
            return Decimal('0.00')
        
        probabilidad = (self.tokens / total_tokens) * 100
        return round(probabilidad, 2)
# Create your models here.
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

# corri esos comandos
# python manage.py makemigrations
# python manage.py migrate


class Usuario(models.Model):
  nombre = models.CharField(max_length=100)
  email = models.EmailField(max_length=150, unique=True)
  saldo = models.DecimalField(max_digits=18, decimal_places=2, default=0,
                              validators=[MinValueValidator(0)])
  racha_actual = models.PositiveIntegerField(default=0)
  ultima_racha = models.DateField(blank=True, null=True)
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
