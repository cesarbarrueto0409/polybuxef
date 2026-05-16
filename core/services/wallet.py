from decimal import Decimal
from core.models import Transaction


class Wallet:
    """
    Capa de lógica de negocio para manejo de saldo del usuario. Modela una billetera del usuario.

    Funciona sobre un sistema de transacciones, donde el saldo no se almacena directamente, sino que se calcula a partir del historial de movimientos IN/OUT.
    """

    def __init__(self, perfil):
        """
        Inicializa la wallet para un perfil específico.

        Args:
            perfil: instancia del modelo Perfil
        """
        self.perfil = perfil

    def obtener_saldo(self) -> Decimal:
        """
        Obtiene el saldo actual del usuario.

        Returns:
            Decimal: saldo calculado desde transacciones
        """
        return self.perfil.obtener_saldo()

    def registrar_transaccion(self, tipo: str, monto: Decimal, descripcion: str = "") -> None:
        """
        Registra una transacción en el sistema.

        Args:
            tipo (str): tipo de transacción ('IN' o 'OUT')
            monto (Decimal): monto de la transacción
            descripcion (str): descripción del movimiento
        """
        Transaction.objects.create(
            perfil=self.perfil,
            tipo=tipo,
            monto=monto,
            descripcion=descripcion
        )

    def agregar_saldo(self, monto: Decimal, descripcion: str = "") -> None:
        """
        Agrega saldo al usuario (ingreso de dinero).

        Args:
            monto (Decimal): monto a agregar
            descripcion (str): descripción del ingreso
        """
        self.registrar_transaccion(
            "IN",
            monto,
            descripcion
        )

    def quitar_saldo(self, monto: Decimal, descripcion: str = "") -> None:
        """
        Retira saldo del usuario si tiene fondos suficientes.

        Args:
            monto (Decimal): monto a retirar
            descripcion (str): descripción del retiro

        Raises:
            ValueError: si el usuario no tiene saldo suficiente
        """
        if self.obtener_saldo() < monto:
            raise ValueError("Saldo insuficiente")

        self.registrar_transaccion(
            "OUT",
            monto,
            descripcion
        )