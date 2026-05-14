from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum

# Create your models here.
from decimal import Decimal

class Perfil(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)

    def obtener_saldo(self):
        ingresos = self.transactions.filter(tipo="IN").aggregate(
            total=Sum("monto")
        )["total"] or Decimal("0")

        egresos = self.transactions.filter(tipo="OUT").aggregate(
            total=Sum("monto")
        )["total"] or Decimal("0")

        return ingresos - egresos


class Transaction(models.Model):
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
