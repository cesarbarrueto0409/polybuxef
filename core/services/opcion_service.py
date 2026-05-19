"""
Servicio de lógica de negocio para gestión de opciones de apuesta.

Proporciona operaciones para crear, consultar y gestionar
opciones dentro de mercados de apuestas.
"""
from core.models import Opcion, Mercado
from django.db import transaction
from decimal import Decimal


class OpcionService:
    """
    Capa de lógica de negocio para gestión de opciones.
    
    Maneja la creación, consulta, actualización y gestión
    de opciones de apuesta dentro de mercados.
    """
    
    @staticmethod
    @transaction.atomic
    def crear_opcion(
        id_mercado: int,
        nombre: str,
        precio_inicial: Decimal = Decimal('0.5000')
    ) -> Opcion:
        """
        Crea una nueva opción de apuesta en un mercado.
        
        Args:
            id_mercado (int): ID del mercado
            nombre (str): nombre de la opción
            precio_inicial (Decimal, optional): precio inicial (default: 0.5)
        
        Returns:
            Opcion: instancia de la opción creada
        
        Raises:
            ValueError: si los datos son inválidos
            Mercado.DoesNotExist: si el mercado no existe
        """
        if not nombre or not nombre.strip():
            raise ValueError("El nombre de la opción no puede estar vacío")
        
        if precio_inicial <= 0 or precio_inicial > 1:
            raise ValueError("El precio inicial debe estar entre 0 y 1")
        
        mercado = Mercado.objects.get(id=id_mercado)
        
        if mercado.estado != 'abierto':
            raise ValueError("No se pueden agregar opciones a un mercado que no está abierto")
        
        opcion = Opcion.objects.create(
            mercado=mercado,
            nombre=nombre.strip(),
            precio=precio_inicial,
            tokens=Decimal('0.00')
        )
        
        return opcion
    
    @staticmethod
    def obtener_opcion(id_opcion: int) -> Opcion:
        """
        Obtiene una opción por su ID.
        
        Args:
            id_opcion (int): ID de la opción
        
        Returns:
            Opcion: instancia de la opción
        
        Raises:
            Opcion.DoesNotExist: si la opción no existe
        """
        return Opcion.objects.get(id=id_opcion)
    
    @staticmethod
    def listar_opciones_por_mercado(id_mercado: int):
        """
        Lista todas las opciones de un mercado.
        
        Args:
            id_mercado (int): ID del mercado
        
        Returns:
            QuerySet[Opcion]: opciones del mercado
        """
        return Opcion.objects.filter(mercado_id=id_mercado)
    
    @staticmethod
    @transaction.atomic
    def agregar_tokens_a_opcion(id_opcion: int, cantidad: Decimal) -> Opcion:
        """
        Agrega tokens a una opción (cuando un usuario compra shares).
        
        Args:
            id_opcion (int): ID de la opción
            cantidad (Decimal): cantidad de tokens a agregar
        
        Returns:
            Opcion: instancia actualizada
        
        Raises:
            ValueError: si la cantidad es inválida o el mercado no está abierto
            Opcion.DoesNotExist: si la opción no existe
        """
        opcion = Opcion.objects.select_related('mercado').get(id=id_opcion)
        
        if not opcion.mercado.esta_abierto():
            raise ValueError("No se pueden agregar tokens a un mercado que no está abierto")
        
        opcion.agregar_tokens(cantidad)
        return opcion
    
    @staticmethod
    @transaction.atomic
    def quitar_tokens_de_opcion(id_opcion: int, cantidad: Decimal) -> Opcion:
        """
        Quita tokens de una opción (cuando un usuario vende shares).
        
        Args:
            id_opcion (int): ID de la opción
            cantidad (Decimal): cantidad de tokens a quitar
        
        Returns:
            Opcion: instancia actualizada
        
        Raises:
            ValueError: si la cantidad es inválida o el mercado no está abierto
            Opcion.DoesNotExist: si la opción no existe
        """
        opcion = Opcion.objects.select_related('mercado').get(id=id_opcion)
        
        if not opcion.mercado.esta_abierto():
            raise ValueError("No se pueden quitar tokens de un mercado que no está abierto")
        
        opcion.quitar_tokens(cantidad)
        return opcion
    
    @staticmethod
    @transaction.atomic
    def actualizar_precio_opcion(id_opcion: int, nuevo_precio: Decimal) -> Opcion:
        """
        Actualiza el precio de una opción.
        
        Args:
            id_opcion (int): ID de la opción
            nuevo_precio (Decimal): nuevo precio
        
        Returns:
            Opcion: instancia actualizada
        
        Raises:
            ValueError: si el precio es inválido
            Opcion.DoesNotExist: si la opción no existe
        """
        opcion = Opcion.objects.get(id=id_opcion)
        opcion.actualizar_precio(nuevo_precio)
        return opcion
    
    @staticmethod
    @transaction.atomic
    def marcar_opcion_ganadora(id_opcion: int) -> Opcion:
        """
        Marca una opción como ganadora y cierra el mercado.
        
        Args:
            id_opcion (int): ID de la opción ganadora
        
        Returns:
            Opcion: instancia de la opción ganadora
        
        Raises:
            ValueError: si el mercado no está cerrado
            Opcion.DoesNotExist: si la opción no existe
        """
        opcion = Opcion.objects.select_related('mercado').get(id=id_opcion)
        
        if opcion.mercado.estado != 'cerrado':
            raise ValueError("Solo se puede marcar ganadora una opción de un mercado cerrado")
        
        # Desmarcar otras opciones ganadoras del mismo mercado
        Opcion.objects.filter(
            mercado=opcion.mercado,
            es_ganadora=True
        ).update(es_ganadora=False)
        
        opcion.marcar_como_ganadora()
        
        # Actualizar estado del mercado a resuelto
        opcion.mercado.estado = 'resuelto'
        opcion.mercado.save()
        
        return opcion
    
    @staticmethod
    def actualizar_opcion(
        id_opcion: int,
        nombre: str = None
    ) -> Opcion:
        """
        Actualiza los datos de una opción.
        
        Args:
            id_opcion (int): ID de la opción
            nombre (str, optional): nuevo nombre
        
        Returns:
            Opcion: instancia actualizada
        
        Raises:
            ValueError: si el nombre es inválido
            Opcion.DoesNotExist: si la opción no existe
        """
        opcion = Opcion.objects.get(id=id_opcion)
        
        if nombre is not None:
            if not nombre.strip():
                raise ValueError("El nombre no puede estar vacío")
            opcion.nombre = nombre.strip()
            opcion.save()
        
        return opcion
    
    @staticmethod
    @transaction.atomic
    def eliminar_opcion(id_opcion: int) -> None:
        """
        Elimina una opción.
        
        Args:
            id_opcion (int): ID de la opción
        
        Raises:
            ValueError: si la opción tiene tokens apostados
            Opcion.DoesNotExist: si la opción no existe
        """
        opcion = Opcion.objects.get(id=id_opcion)
        
        if opcion.tokens > 0:
            raise ValueError("No se puede eliminar una opción con tokens apostados")
        
        opcion.delete()
    
    @staticmethod
    def obtener_probabilidades_mercado(id_mercado: int):
        """
        Calcula las probabilidades de todas las opciones de un mercado.
        
        Args:
            id_mercado (int): ID del mercado
        
        Returns:
            dict: diccionario con id_opcion como clave y probabilidad como valor
        """
        opciones = Opcion.objects.filter(mercado_id=id_mercado)
        probabilidades = {}
        
        for opcion in opciones:
            probabilidades[opcion.id] = opcion.calcular_probabilidad()
        
        return probabilidades
