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

    def __init__(self, profile):
        """
        Inicializa la wallet para un perfil específico.

        Args:
            profile: instancia del modelo Profile
        """
        self.profile = profile

    def get_balance(self) -> Decimal:
        """
        Obtiene el saldo actual del usuario.

        Returns:
            Decimal: saldo calculado desde transacciones
        """
        return self.profile.get_balance()

    # Funciones básicas de la wallet

    def register_transaction(self, kind: str, category: str, amount: Decimal, description: str = "") -> None:
        """
        Registra una transacción en el sistema.

        Args:
            kind (str): tipo de transacción ('IN' o 'OUT')
            category (str): categoría de la transacción
            amount (Decimal): monto de la transacción
            description (str): descripción del movimiento
        
        Raises:
            ValueError: si el monto es inválido (igual o menor a cero)
        """
        if amount <= 0:
            raise ValueError("El monto debe ser mayor a 0")

        Transaction.objects.create(
            profile=self.profile,
            kind=kind,
            category=category,
            amount=amount,
            description=description
        )
    
    def revert_transaction(self, transaction: Transaction) -> None:
        """
        Revierte una transacción creando un movimiento inverso.

        La transacción original no se elimina, sino que se
        marca como revertida para mantener trazabilidad
        e historial financiero.

        Args:
            transaction (Transaction): transacción a revertir

        Raises:
            ValueError: si la transacción ya fue revertida
        """

        if transaction.reverted:
            raise ValueError("La transacción ya fue revertida")

        if transaction.profile != self.profile:
            raise ValueError("La transacción no pertenece a esta wallet")
        
        if transaction.kind == "IN":
            reverse_type = "OUT"
        else:
            reverse_type = "IN"

        self.register_transaction(
            reverse_type,
            transaction.category,
            transaction.amount,
            f"Reversión de transacción #{transaction.id}"
        )

        transaction.reverted = True
        transaction.save()

    def add_balance(self, category: str, amount: Decimal, description: str = "") -> None:
        """
        Agrega saldo al usuario (ingreso de dinero).

        Args:
            amount (Decimal): monto a agregar
            category (str): categoría de la transacción
            description (str): descripción del ingreso

        Raises:
            ValueError: si el monto es inválido (igual o menor a cero)
        """
        self.register_transaction(
            "IN",
            category,
            amount,
            description
        )

    def subtract_balance(self, category: str, amount: Decimal, description: str = "") -> None:
        """
        Retira saldo del usuario si tiene fondos suficientes.

        Args:
            amount (Decimal): monto a retirar
            category (str): categoría de la transacción
            description (str): descripción del retiro

        Raises:
            ValueError: si el monto es inválido (igual o menor a cero)
            ValueError: si el usuario no tiene saldo suficiente
        """
        if self.get_balance() < amount:
            raise ValueError("Saldo insuficiente")
        
        self.register_transaction(
            "OUT",
            category,
            amount,
            description
        )

    # Wrappers, no agregan lógica nueva

    #TODO: cuando estén listas las apuestas, se debe entregar como parámetro un id a la apuesta/opción a comprar
    def buy_shares(self, amount: Decimal, description: str = ""):
        self.subtract_balance(
            "BET_BUY",
            amount,
            description
        )

    #TODO: cuando estén listas las apuestas, se debe entregar como parámetro un id a la apuesta/opción que se vende
    def sell_shares(self, amount: Decimal, description: str = ""):
        self.add_balance(
            "BET_SELL",
            amount,
            description
        )

    #TODO: cuando estén listas las apuestas, se debe agregar de qué apuesta viene la recompensa (validación)
    def grant_bet_reward(self, amount: Decimal, description: str = ""):
        self.add_balance(
            "BET_REWARD",
            amount,
            description
        )

    #TODO: cuando esté listo el day streak, reformular función para otorgar recompensas según el día correspondiente
    def grant_streak_reward(self, amount: Decimal, description: str = ""):
        self.add_balance(
            "STREAK_REWARD",
            amount,
            description
        )

    def admin_grant_balance(self, amount: Decimal, description: str = ""):
        self.add_balance(
            "ADMIN_GRANT",
            amount,
            description
        )

    def admin_remove_balance(self, amount: Decimal, description: str = ""):
        self.subtract_balance(
            "ADMIN_REMOVE",
            amount,
            description
        )