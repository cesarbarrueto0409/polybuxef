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