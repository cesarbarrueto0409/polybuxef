from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum
from decimal import Decimal


class Perfil(models.Model):
    """
    Perfil de usuario del sistema.

    Relación 1 a 1 con el usuario de Django.
    Calcula el saldo del usuario a partir de sus transacciones (ledger system).
    """

    usuario = models.OneToOneField(User, on_delete=models.CASCADE)

    def obtener_saldo(self) -> Decimal:
        """
        Calcula el saldo actual del usuario sumando ingresos y egresos.

        Returns:
            Decimal: saldo actual del usuario
        """
        ingresos = self.transactions.filter(tipo="IN").aggregate(
            total=Sum("monto")
        )["total"] or Decimal("0")

        egresos = self.transactions.filter(tipo="OUT").aggregate(
            total=Sum("monto")
        )["total"] or Decimal("0")

        return ingresos - egresos


class Transaction(models.Model):
    """
    Registro de transacciones del sistema.

    Representa movimientos de dinero del usuario:
    - IN: ingreso de dinero
    - OUT: salida de dinero
    """

    TIPO_CHOICES = [
        ("IN", "Ingreso"),
        ("OUT", "Egreso"),
    ]

    perfil = models.ForeignKey(
        Perfil,
        on_delete=models.CASCADE,
        related_name="transactions"
    )

    tipo = models.CharField(max_length=3, choices=TIPO_CHOICES)
    monto = models.DecimalField(max_digits=12, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)