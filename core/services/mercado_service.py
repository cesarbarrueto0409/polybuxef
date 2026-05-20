"""
Servicio de lógica de negocio para gestión de mercados.

Proporciona operaciones para crear, consultar y gestionar
el ciclo de vida de mercados de apuestas.
"""
from core.models import Mercado, Categoria
from django.db import transaction
from django.utils import timezone
from datetime import datetime


class MercadoService:
    """
    Capa de lógica de negocio para gestión de mercados.
    
    Maneja la creación, consulta, actualización y cierre
    de mercados de apuestas.
    """
    
    @staticmethod
    @transaction.atomic
    def crear_mercado(
        id_categoria: int,
        titulo: str,
        descripcion: str,
        fecha_cierre: datetime,
        imagen_url: str = None
    ) -> Mercado:
        """
        Crea un nuevo mercado de apuestas.
        
        Args:
            id_categoria (int): ID de la categoría
            titulo (str): título del mercado
            descripcion (str): descripción del mercado
            fecha_cierre (datetime): fecha límite para apuestas
            imagen_url (str, optional): URL de la imagen
        
        Returns:
            Mercado: instancia del mercado creado
        
        Raises:
            ValueError: si los datos son inválidos
            Categoria.DoesNotExist: si la categoría no existe
        """
        if not titulo or not titulo.strip():
            raise ValueError("El título no puede estar vacío")
        
        if not descripcion or not descripcion.strip():
            raise ValueError("La descripción no puede estar vacía")
        
        if fecha_cierre <= timezone.now():
            raise ValueError("La fecha de cierre debe ser futura")
        
        categoria = Categoria.objects.get(id=id_categoria)
        
        mercado = Mercado.objects.create(
            categoria=categoria,
            titulo=titulo.strip(),
            descripcion=descripcion.strip(),
            fecha_cierre=fecha_cierre,
            imagen_url=imagen_url,
            estado='abierto'
        )
        
        return mercado
    
    @staticmethod
    def obtener_mercado(id_mercado: int) -> Mercado:
        """
        Obtiene un mercado por su ID.
        
        Args:
            id_mercado (int): ID del mercado
        
        Returns:
            Mercado: instancia del mercado
        
        Raises:
            Mercado.DoesNotExist: si el mercado no existe
        """
        return Mercado.objects.get(id=id_mercado)
    
    @staticmethod
    def listar_mercados():
        """
        Lista todos los mercados ordenados por fecha de creación.
        
        Returns:
            QuerySet[Mercado]: todos los mercados
        """
        return Mercado.objects.all()
    
    @staticmethod
    def listar_mercados_abiertos():
        """
        Lista mercados con estado 'abierto'.
        
        Returns:
            QuerySet[Mercado]: mercados abiertos
        """
        return Mercado.objects.filter(estado='abierto')
    
    @staticmethod
    def listar_mercados_por_categoria(id_categoria: int):
        """
        Lista mercados de una categoría específica.
        
        Args:
            id_categoria (int): ID de la categoría
        
        Returns:
            QuerySet[Mercado]: mercados de la categoría
        """
        return Mercado.objects.filter(categoria_id=id_categoria)
    
    @staticmethod
    @transaction.atomic
    def cerrar_mercado(id_mercado: int) -> Mercado:
        """
        Cierra un mercado, impidiendo nuevas apuestas.
        
        Args:
            id_mercado (int): ID del mercado
        
        Returns:
            Mercado: instancia del mercado cerrado
        
        Raises:
            ValueError: si el mercado no está abierto
            Mercado.DoesNotExist: si el mercado no existe
        """
        mercado = Mercado.objects.get(id=id_mercado)
        
        if mercado.estado != 'abierto':
            raise ValueError(f"El mercado no está abierto (estado actual: {mercado.estado})")
        
        mercado.cerrar_mercado()
        return mercado
    
    @staticmethod
    @transaction.atomic
    def cancelar_mercado(id_mercado: int) -> Mercado:
        """
        Cancela un mercado.
        
        Args:
            id_mercado (int): ID del mercado
        
        Returns:
            Mercado: instancia del mercado cancelado
        
        Raises:
            ValueError: si el mercado ya está resuelto
            Mercado.DoesNotExist: si el mercado no existe
        """
        mercado = Mercado.objects.get(id=id_mercado)
        
        if mercado.estado == 'resuelto':
            raise ValueError("No se puede cancelar un mercado ya resuelto")
        
        mercado.cancelar_mercado()
        return mercado
    
    @staticmethod
    def actualizar_mercado(
        id_mercado: int,
        titulo: str = None,
        descripcion: str = None,
        imagen_url: str = None,
        fecha_cierre: datetime = None
    ) -> Mercado:
        """
        Actualiza los datos de un mercado.
        
        Args:
            id_mercado (int): ID del mercado
            titulo (str, optional): nuevo título
            descripcion (str, optional): nueva descripción
            imagen_url (str, optional): nueva URL de imagen
            fecha_cierre (datetime, optional): nueva fecha de cierre
        
        Returns:
            Mercado: instancia actualizada
        
        Raises:
            ValueError: si los datos son inválidos
            Mercado.DoesNotExist: si el mercado no existe
        """
        mercado = Mercado.objects.get(id=id_mercado)
        
        if titulo is not None:
            if not titulo.strip():
                raise ValueError("El título no puede estar vacío")
            mercado.titulo = titulo.strip()
        
        if descripcion is not None:
            if not descripcion.strip():
                raise ValueError("La descripción no puede estar vacía")
            mercado.descripcion = descripcion.strip()
        
        if imagen_url is not None:
            mercado.imagen_url = imagen_url
        
        if fecha_cierre is not None:
            if fecha_cierre <= timezone.now():
                raise ValueError("La fecha de cierre debe ser futura")
            mercado.fecha_cierre = fecha_cierre
        
        mercado.save()
        return mercado
    
    @staticmethod
    @transaction.atomic
    def eliminar_mercado(id_mercado: int) -> None:
        """
        Elimina un mercado.
        
        ADVERTENCIA: Esto eliminará en cascada todas las opciones
        asociadas a este mercado.
        
        Args:
            id_mercado (int): ID del mercado
        
        Raises:
            Mercado.DoesNotExist: si el mercado no existe
        """
        mercado = Mercado.objects.get(id=id_mercado)
        mercado.delete()
