from decimal import Decimal
from core.models import Transaction


class Wallet:
    """
    Capa de lógica de negocio para manejo de saldo del usuario.
    Modela una billetera del usuario.

    Funciona sobre un sistema de transacciones, donde
    el saldo no se almacena directamente, sino que se
    calcula a partir del historial de movimientos IN/OUT.
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

    def registrar_transaccion(self, tipo: str, categoria: str, monto: Decimal, descripcion: str = "") -> None:
        """
        Registra una transacción en el sistema.

        Args:
            tipo (str): tipo de transacción ('IN' o 'OUT')
            categoria (str): categoría de la transacción
            monto (Decimal): monto de la transacción
            descripcion (str): descripción del movimiento
        
        Raises:
            ValueError: si el monto es inválido (igual o menor a cero)
        """
        if monto <= 0:
            raise ValueError("El monto debe ser mayor a 0")

        Transaction.objects.create(
            perfil=self.perfil,
            tipo=tipo,
            categoria=categoria,
            monto=monto,
            descripcion=descripcion
        )

    def agregar_saldo(self, categoria: str, monto: Decimal, descripcion: str = "") -> None:
        """
        Agrega saldo al usuario (ingreso de dinero).

        Args:
            monto (Decimal): monto a agregar
            categoria (str): categoría de la transacción
            descripcion (str): descripción del ingreso

        Raises:
            ValueError: si el monto es inválido (igual o menor a cero)
        """
        self.registrar_transaccion(
            "IN",
            categoria,
            monto,
            descripcion
        )

    def quitar_saldo(self, categoria: str, monto: Decimal, descripcion: str = "") -> None:
        """
        Retira saldo del usuario si tiene fondos suficientes.

        Args:
            monto (Decimal): monto a retirar
            categoria (str): categoría de la transacción
            descripcion (str): descripción del retiro

        Raises:
            ValueError: si el monto es inválido (igual o menor a cero)
            ValueError: si el usuario no tiene saldo suficiente
        """
        if self.obtener_saldo() < monto:
            raise ValueError("Saldo insuficiente")
        
        self.registrar_transaccion(
            "OUT",
            categoria,
            monto,
            descripcion
        )