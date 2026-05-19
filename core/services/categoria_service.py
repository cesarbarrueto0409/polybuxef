"""
Servicio de lógica de negocio para gestión de categorías.

Proporciona operaciones CRUD y consultas sobre categorías de mercados.
"""
from core.models import Categoria
from django.db import transaction


class CategoriaService:
    """
    Capa de lógica de negocio para gestión de categorías.
    
    Maneja la creación, consulta, actualización y eliminación
    de categorías de mercados de apuestas.
    """
    
    @staticmethod
    def crear_categoria(nombre: str) -> Categoria:
        """
        Crea una nueva categoría.
        
        Args:
            nombre (str): nombre de la categoría
        
        Returns:
            Categoria: instancia de la categoría creada
        
        Raises:
            ValueError: si el nombre está vacío o ya existe
        """
        if not nombre or not nombre.strip():
            raise ValueError("El nombre de la categoría no puede estar vacío")
        
        nombre = nombre.strip()
        
        if Categoria.objects.filter(nombre=nombre).exists():
            raise ValueError(f"Ya existe una categoría con el nombre '{nombre}'")
        
        categoria = Categoria.objects.create(nombre=nombre)
        return categoria
    
    @staticmethod
    def obtener_categoria(id_categoria: int) -> Categoria:
        """
        Obtiene una categoría por su ID.
        
        Args:
            id_categoria (int): ID de la categoría
        
        Returns:
            Categoria: instancia de la categoría
        
        Raises:
            Categoria.DoesNotExist: si la categoría no existe
        """
        return Categoria.objects.get(id=id_categoria)
    
    @staticmethod
    def listar_categorias():
        """
        Lista todas las categorías ordenadas alfabéticamente.
        
        Returns:
            QuerySet[Categoria]: todas las categorías
        """
        return Categoria.objects.all()
    
    @staticmethod
    def actualizar_categoria(id_categoria: int, nombre: str) -> Categoria:
        """
        Actualiza el nombre de una categoría.
        
        Args:
            id_categoria (int): ID de la categoría
            nombre (str): nuevo nombre
        
        Returns:
            Categoria: instancia actualizada
        
        Raises:
            ValueError: si el nombre es inválido o ya existe
            Categoria.DoesNotExist: si la categoría no existe
        """
        if not nombre or not nombre.strip():
            raise ValueError("El nombre de la categoría no puede estar vacío")
        
        nombre = nombre.strip()
        categoria = Categoria.objects.get(id=id_categoria)
        
        if Categoria.objects.filter(nombre=nombre).exclude(id=id_categoria).exists():
            raise ValueError(f"Ya existe otra categoría con el nombre '{nombre}'")
        
        categoria.nombre = nombre
        categoria.save()
        return categoria
    
    @staticmethod
    @transaction.atomic
    def eliminar_categoria(id_categoria: int) -> None:
        """
        Elimina una categoría.
        
        ADVERTENCIA: Esto eliminará en cascada todos los mercados
        y opciones asociadas a esta categoría.
        
        Args:
            id_categoria (int): ID de la categoría
        
        Raises:
            Categoria.DoesNotExist: si la categoría no existe
        """
        categoria = Categoria.objects.get(id=id_categoria)
        categoria.delete()
    
    @staticmethod
    def obtener_categorias_con_mercados_activos():
        """
        Obtiene categorías que tienen al menos un mercado abierto.
        
        Returns:
            QuerySet[Categoria]: categorías con mercados activos
        """
        return Categoria.objects.filter(
            mercados__estado='abierto'
        ).distinct()
