"""
Servicio de lógica de negocio para el sistema de ruleta y coleccionables.

Maneja la compra de giros, giro de la ruleta, selección aleatoria ponderada
y asignación de coleccionables a usuarios.
"""
import random
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from core.models import (
    Usuario,
    Coleccionable,
    UsuarioColeccionable,
    RuletaProbabilidad,
    ConfiguracionRuleta,
    HistorialRuleta
)


class RuletaService:
    """
    Capa de lógica de negocio para el sistema de ruleta.
    
    Maneja la compra de giros, el giro de la ruleta con probabilidades
    ponderadas, y la asignación de coleccionables a los usuarios.
    """
    
    @staticmethod
    def obtener_configuracion():
        """
        Obtiene la configuración actual de la ruleta.
        
        Returns:
            ConfiguracionRuleta: Configuración actual
        """
        return ConfiguracionRuleta.obtener_configuracion()
    
    @staticmethod
    @transaction.atomic
    def comprar_giros(id_usuario: int, cantidad: int = 1):
        """
        Compra giros para la ruleta descontando saldo del usuario.
        
        Args:
            id_usuario (int): ID del usuario
            cantidad (int): Cantidad de giros a comprar (default: 1)
        
        Returns:
            dict: Información de la compra
        
        Raises:
            ValueError: Si no tiene saldo suficiente o la ruleta está inactiva
            Usuario.DoesNotExist: Si el usuario no existe
        """
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor a 0")
        
        # Obtener configuración
        config = ConfiguracionRuleta.obtener_configuracion()
        
        if not config.activa:
            raise ValueError("La ruleta no está activa en este momento")
        
        # Calcular costo total
        costo_total = config.costo_giro * cantidad
        
        # Obtener usuario
        usuario = Usuario.objects.select_for_update().get(id=id_usuario)
        
        # Verificar saldo
        if not usuario.tiene_saldo_suficiente(costo_total):
            raise ValueError(
                f"Saldo insuficiente. Necesitas ${costo_total}, tienes ${usuario.saldo}"
            )
        
        # Descontar saldo
        usuario.descontar_saldo(costo_total)
        
        # Agregar giros
        usuario.agregar_giros(cantidad)
        
        return {
            'usuario': usuario,
            'giros_comprados': cantidad,
            'costo_total': costo_total,
            'saldo_restante': usuario.saldo,
            'giros_totales': usuario.giros_disponibles
        }
    
    @staticmethod
    def _seleccionar_coleccionable_aleatorio():
        """
        Selecciona un coleccionable aleatorio basado en probabilidades ponderadas.
        
        Returns:
            Coleccionable: Coleccionable seleccionado
        
        Raises:
            ValueError: Si no hay coleccionables activos
        """
        # Obtener probabilidades activas
        probabilidades = RuletaProbabilidad.objects.filter(
            activo=True
        ).select_related('coleccionable')
        
        if not probabilidades.exists():
            raise ValueError("No hay coleccionables disponibles en la ruleta")
        
        # Extraer coleccionables y sus pesos
        coleccionables = [p.coleccionable for p in probabilidades]
        pesos = [float(p.probabilidad) for p in probabilidades]
        
        # Normalizar pesos (asegurar que sumen 1)
        suma_pesos = sum(pesos)
        if suma_pesos == 0:
            raise ValueError("Las probabilidades suman 0")
        
        pesos_normalizados = [p / suma_pesos for p in pesos]
        
        # Selección aleatoria ponderada
        coleccionable_ganado = random.choices(
            coleccionables,
            weights=pesos_normalizados,
            k=1
        )[0]
        
        return coleccionable_ganado
    
    @staticmethod
    @transaction.atomic
    def girar_ruleta(id_usuario: int):
        """
        Gira la ruleta y asigna un coleccionable al usuario.
        
        Args:
            id_usuario (int): ID del usuario
        
        Returns:
            dict: Información del giro (coleccionable obtenido, si es nuevo, etc.)
        
        Raises:
            ValueError: Si no tiene giros disponibles
            Usuario.DoesNotExist: Si el usuario no existe
        """
        # Obtener usuario con lock
        usuario = Usuario.objects.select_for_update().get(id=id_usuario)
        
        # Verificar giros disponibles
        if not usuario.tiene_giros_disponibles():
            raise ValueError("No tienes giros disponibles. Compra giros primero.")
        
        # Obtener configuración para el costo
        config = ConfiguracionRuleta.obtener_configuracion()
        
        # Seleccionar coleccionable aleatorio
        coleccionable_ganado = RuletaService._seleccionar_coleccionable_aleatorio()
        
        # Verificar si ya lo tiene
        inventario, es_nuevo = UsuarioColeccionable.objects.get_or_create(
            usuario=usuario,
            coleccionable=coleccionable_ganado
        )
        
        if not es_nuevo:
            # Ya lo tenía, incrementar cantidad
            inventario.incrementar_cantidad()
        
        # Registrar en historial
        HistorialRuleta.objects.create(
            usuario=usuario,
            coleccionable_obtenido=coleccionable_ganado,
            costo=config.costo_giro
        )
        
        # Descontar giro
        usuario.descontar_giro()
        
        return {
            'coleccionable': coleccionable_ganado,
            'es_nuevo': es_nuevo,
            'cantidad_total': inventario.cantidad,
            'giros_restantes': usuario.giros_disponibles,
            'rareza': coleccionable_ganado.rareza
        }
    
    @staticmethod
    def obtener_coleccionables_usuario(id_usuario: int):
        """
        Obtiene todos los coleccionables que posee un usuario.
        
        Args:
            id_usuario (int): ID del usuario
        
        Returns:
            QuerySet: Coleccionables del usuario con información de cantidad
        """
        return UsuarioColeccionable.objects.filter(
            usuario_id=id_usuario
        ).select_related('coleccionable').order_by('-fecha_obtencion')
    
    @staticmethod
    def obtener_coleccionables_faltantes(id_usuario: int):
        """
        Obtiene los coleccionables que le faltan al usuario.
        
        Args:
            id_usuario (int): ID del usuario
        
        Returns:
            QuerySet: Coleccionables que no tiene el usuario
        """
        usuario = Usuario.objects.get(id=id_usuario)
        
        # IDs de coleccionables que ya tiene
        ids_obtenidos = usuario.coleccionables_obtenidos.values_list(
            'coleccionable_id',
            flat=True
        )
        
        # Coleccionables que no tiene
        return Coleccionable.objects.exclude(id__in=ids_obtenidos)
    
    @staticmethod
    def obtener_estadisticas_usuario(id_usuario: int):
        """
        Obtiene estadísticas del progreso del usuario en coleccionables.
        
        Args:
            id_usuario (int): ID del usuario
        
        Returns:
            dict: Estadísticas del usuario
        """
        usuario = Usuario.objects.get(id=id_usuario)
        
        total_coleccionables = Coleccionable.objects.count()
        coleccionables_obtenidos = usuario.coleccionables_obtenidos.count()
        coleccionables_faltantes = total_coleccionables - coleccionables_obtenidos
        
        porcentaje_completado = (
            (coleccionables_obtenidos / total_coleccionables * 100)
            if total_coleccionables > 0 else 0
        )
        
        # Estadísticas por rareza
        rareza_stats = {}
        for rareza, _ in Coleccionable.RAREZA_CHOICES:
            total_rareza = Coleccionable.objects.filter(rareza=rareza).count()
            obtenidos_rareza = usuario.coleccionables_obtenidos.filter(
                coleccionable__rareza=rareza
            ).count()
            
            rareza_stats[rareza] = {
                'total': total_rareza,
                'obtenidos': obtenidos_rareza,
                'faltantes': total_rareza - obtenidos_rareza
            }
        
        # Total de giros realizados
        total_giros = usuario.historial_ruletas.count()
        
        return {
            'usuario': usuario,
            'total_coleccionables': total_coleccionables,
            'coleccionables_obtenidos': coleccionables_obtenidos,
            'coleccionables_faltantes': coleccionables_faltantes,
            'porcentaje_completado': round(porcentaje_completado, 2),
            'rareza_stats': rareza_stats,
            'total_giros': total_giros,
            'giros_disponibles': usuario.giros_disponibles
        }
    
    @staticmethod
    def obtener_historial_giros(id_usuario: int, limit: int = 10):
        """
        Obtiene el historial de giros del usuario.
        
        Args:
            id_usuario (int): ID del usuario
            limit (int): Cantidad máxima de registros (default: 10)
        
        Returns:
            QuerySet: Historial de giros del usuario
        """
        return HistorialRuleta.objects.filter(
            usuario_id=id_usuario
        ).select_related('coleccionable_obtenido').order_by('-fecha')[:limit]
    
    @staticmethod
    def listar_todos_coleccionables():
        """
        Lista todos los coleccionables disponibles en el sistema.
        
        Returns:
            QuerySet: Todos los coleccionables
        """
        return Coleccionable.objects.all()
    
    @staticmethod
    def obtener_probabilidades_activas():
        """
        Obtiene las probabilidades de todos los coleccionables activos.
        
        Returns:
            QuerySet: Probabilidades de la ruleta activas
        """
        return RuletaProbabilidad.objects.filter(
            activo=True
        ).select_related('coleccionable').order_by('-probabilidad')
