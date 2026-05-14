from decimal import Decimal
from core.models import Transaction

class Wallet:
    def __init__(self, perfil):
        self.perfil = perfil

    def obtener_saldo(self) -> Decimal:
        return self.perfil.obtener_saldo()

    def registrar_transaccion(self, tipo: str, monto: Decimal) -> None:
        Transaction.objects.create(
            perfil=self.perfil,
            tipo=tipo,
            monto=monto
        )

    def agregar_saldo(self, monto: Decimal) -> None:
        self.registrar_transaccion("IN", monto)

    def quitar_saldo(self, monto: Decimal) -> None:
        if self.obtener_saldo() < monto:
            raise ValueError("Saldo insuficiente")

        self.registrar_transaccion("OUT", monto)




