from django.db import models
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
