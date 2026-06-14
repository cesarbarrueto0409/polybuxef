from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from core.models import HistorialPrecio, Mercado, Opcion, Resolucion, TransaccionShare, Usuario


def _recompensa_racha(dias):
    """
    Calcula la recompensa según los días de racha.
    Máximo 5 días, cada día suma $100.
    """
    return min(dias, 5) * 100


def obtener_estado_racha(id_usuario):
    """
    Obtiene el estado actual de la racha diaria de un usuario.
    
    Args:
        id_usuario: ID del Usuario
        
    Returns:
        dict con información de la racha actual
    """
    hoy = timezone.localdate()
    usuario = Usuario.objects.get(id=id_usuario)

    ya_cobrada_hoy = usuario.ultima_racha == hoy
    if ya_cobrada_hoy:
        racha_actual = usuario.racha_actual
        recompensa_hoy = 0
        estado_racha = "Ya cobraste tu racha hoy"
    elif usuario.ultima_racha == hoy - timedelta(days=1):
        racha_actual = usuario.racha_actual + 1
        recompensa_hoy = _recompensa_racha(racha_actual)
        estado_racha = "Tienes una racha lista para cobrar"
    else:
        racha_actual = 1
        recompensa_hoy = _recompensa_racha(racha_actual)
        estado_racha = "Tu racha diaria te esta esperando"

    return {
        "racha_actual": racha_actual,
        "recompensa_hoy": recompensa_hoy,
        "recompensa_siguiente": _recompensa_racha(racha_actual + 1),
        "ya_cobrada_hoy": ya_cobrada_hoy,
        "puede_canjear": not ya_cobrada_hoy,
        "estado_racha": estado_racha,
    }


def canjear_racha_diaria(id_usuario):
    """
    Canjea la racha diaria del usuario y agrega saldo.
    
    Args:
        id_usuario: ID del Usuario
        
    Returns:
        dict con estado de racha y recompensa cobrada
    """
    hoy = timezone.localdate()
    recompensa_cobrada = Decimal("0")

    with transaction.atomic():
        usuario = Usuario.objects.select_for_update().get(id=id_usuario)

        if usuario.ultima_racha != hoy:
            # Determinar si continúa la racha o reinicia
            if usuario.ultima_racha == hoy - timedelta(days=1):
                usuario.racha_actual += 1
            else:
                usuario.racha_actual = 1

            # Calcular y otorgar recompensa
            recompensa_cobrada = Decimal(_recompensa_racha(usuario.racha_actual))
            usuario.saldo += recompensa_cobrada
            usuario.ultima_racha = hoy
            usuario.save(update_fields=["racha_actual", "ultima_racha", "saldo"])

    estado = obtener_estado_racha(id_usuario)
    estado["recompensa_cobrada"] = float(recompensa_cobrada)
    return estado


def comprar(id_usuario, id_opcion, monto):
    """
    Compra shares de una opción en un mercado.
    
    Args:
        id_usuario: ID del Usuario (core.models.Usuario)
        id_opcion: ID de la Opción a comprar
        monto: Monto a invertir
        
    Returns:
        dict con shares y precio_unitario
        
    Raises:
        ValueError: Si el mercado no está disponible o saldo insuficiente
    """
    monto = Decimal(str(monto))
    with transaction.atomic():
        usuario = Usuario.objects.select_for_update().get(id=id_usuario)
        opcion = Opcion.objects.select_for_update().get(id=id_opcion)
        mercado = Mercado.objects.select_for_update().get(id=opcion.mercado_id)

        if mercado.estado != "abierto" or mercado.fecha_cierre <= timezone.now():
            raise ValueError("Mercado no disponible")
            
        if usuario.saldo < monto:
            raise ValueError("Saldo insuficiente")

        opcion_contraria = (
            Opcion.objects.select_for_update()
            .exclude(id=opcion.id)
            .get(mercado=mercado)
        )

        # Calcular shares usando fórmula AMM
        tokens_a = opcion.tokens
        tokens_b = opcion_contraria.tokens
        k = tokens_a * tokens_b
        nuevo_tokens_b = tokens_b + monto
        nuevo_tokens_a = k / nuevo_tokens_b
        shares = tokens_a - nuevo_tokens_a
        nuevo_precio_a = nuevo_tokens_b / (nuevo_tokens_a + nuevo_tokens_b)
        precio_unitario = monto / shares

        # Descontar saldo del usuario
        usuario.saldo -= monto
        usuario.save(update_fields=["saldo"])

        # Actualizar tokens y precios
        opcion.tokens = nuevo_tokens_a
        opcion.precio = nuevo_precio_a
        opcion.save(update_fields=["tokens", "precio"])

        opcion_contraria.tokens = nuevo_tokens_b
        opcion_contraria.precio = 1 - nuevo_precio_a
        opcion_contraria.save(update_fields=["tokens", "precio"])

        # Registrar transacción
        TransaccionShare.objects.create(
            usuario=usuario,
            opcion=opcion,
            tipo="compra",
            shares=shares,
            monto=monto,
            precio_unitario=precio_unitario,
        )
        
        # Guardar historial de precios
        HistorialPrecio.objects.create(opcion=opcion, precio=nuevo_precio_a)
        HistorialPrecio.objects.create(opcion=opcion_contraria, precio=1 - nuevo_precio_a)

        # Actualizar liquidez del mercado
        mercado.liquidez_total += monto
        mercado.save(update_fields=["liquidez_total"])

        return {"shares": float(shares), "precio_unitario": float(precio_unitario)}


def vender(id_usuario, id_opcion, shares):
    """
    Vende shares de una opción en un mercado.
    
    Args:
        id_usuario: ID del Usuario
        id_opcion: ID de la Opción a vender
        shares: Cantidad de shares a vender
        
    Returns:
        dict con monto y precio_unitario
        
    Raises:
        ValueError: Si el mercado no está disponible o shares insuficientes
    """
    shares = Decimal(str(shares))
    with transaction.atomic():
        usuario = Usuario.objects.select_for_update().get(id=id_usuario)
        opcion = Opcion.objects.select_for_update().get(id=id_opcion)
        mercado = Mercado.objects.select_for_update().get(id=opcion.mercado_id)

        if mercado.estado != "abierto" or mercado.fecha_cierre <= timezone.now():
            raise ValueError("Mercado no disponible")

        # Calcular shares disponibles
        compras = (
            TransaccionShare.objects.filter(usuario=usuario, opcion=opcion, tipo="compra")
            .aggregate(t=Sum("shares"))["t"] or Decimal(0)
        )
        ventas = (
            TransaccionShare.objects.filter(usuario=usuario, opcion=opcion, tipo="venta")
            .aggregate(t=Sum("shares"))["t"] or Decimal(0)
        )
        shares_disponibles = compras - ventas

        if shares_disponibles < shares:
            raise ValueError("Shares insuficientes")

        opcion_contraria = (
            Opcion.objects.select_for_update()
            .exclude(id=opcion.id)
            .get(mercado=mercado)
        )

        # Calcular monto usando fórmula AMM
        tokens_a = opcion.tokens
        tokens_b = opcion_contraria.tokens
        k = tokens_a * tokens_b
        nuevo_tokens_a = tokens_a + shares
        nuevo_tokens_b = k / nuevo_tokens_a
        monto = tokens_b - nuevo_tokens_b
        nuevo_precio_a = nuevo_tokens_b / (nuevo_tokens_a + nuevo_tokens_b)
        precio_unitario = monto / shares

        # Actualizar tokens y precios
        opcion.tokens = nuevo_tokens_a
        opcion.precio = nuevo_precio_a
        opcion.save(update_fields=["tokens", "precio"])

        opcion_contraria.tokens = nuevo_tokens_b
        opcion_contraria.precio = 1 - nuevo_precio_a
        opcion_contraria.save(update_fields=["tokens", "precio"])

        # Agregar saldo al usuario
        usuario.saldo += monto
        usuario.save(update_fields=["saldo"])

        # Registrar transacción
        TransaccionShare.objects.create(
            usuario=usuario,
            opcion=opcion,
            tipo="venta",
            shares=shares,
            monto=monto,
            precio_unitario=precio_unitario,
        )
        
        # Guardar historial de precios
        HistorialPrecio.objects.create(opcion=opcion, precio=nuevo_precio_a)
        HistorialPrecio.objects.create(opcion=opcion_contraria, precio=1 - nuevo_precio_a)

        # Actualizar liquidez del mercado
        mercado.liquidez_total -= monto
        mercado.save(update_fields=["liquidez_total"])

        return {"monto": float(monto), "precio_unitario": float(precio_unitario)}


def resolver_mercado(mercado_id, opcion_ganadora_id):
    """
    Resuelve un mercado marcando la opción ganadora.
    
    Args:
        mercado_id: ID del Mercado
        opcion_ganadora_id: ID de la Opción ganadora
        
    Returns:
        dict con mercado_id y opcion_ganadora
        
    Raises:
        ValueError: Si el mercado ya fue resuelto o cancelado
    """
    with transaction.atomic():
        mercado = Mercado.objects.select_for_update().get(id=mercado_id)
        if mercado.estado == "resuelto":
            raise ValueError("El mercado ya fue resuelto")
        if mercado.estado == "cancelado":
            raise ValueError("El mercado está cancelado")

        opcion_ganadora = Opcion.objects.get(id=opcion_ganadora_id, mercado=mercado)

        # Marcar opción ganadora
        Opcion.objects.filter(mercado=mercado).update(es_ganadora=False)
        opcion_ganadora.es_ganadora = True
        opcion_ganadora.save(update_fields=["es_ganadora"])

        # Cambiar estado del mercado
        mercado.estado = "resuelto"
        mercado.save(update_fields=["estado"])

        # Crear registro de resolución
        Resolucion.objects.create(mercado=mercado, opcion_ganadora=opcion_ganadora)

        return {"mercado_id": mercado.id, "opcion_ganadora": opcion_ganadora.nombre}


def redimir(id_usuario, id_opcion):
    """
    Redime shares ganadores de una opción resuelta.
    
    Args:
        id_usuario: ID del Usuario
        id_opcion: ID de la Opción ganadora
        
    Returns:
        dict con shares y monto redimido
        
    Raises:
        ValueError: Si la opción no es ganadora o no hay shares para redimir
    """
    with transaction.atomic():
        usuario = Usuario.objects.select_for_update().get(id=id_usuario)
        opcion = Opcion.objects.select_for_update().get(id=id_opcion)

        if opcion.es_ganadora is not True:
            raise ValueError("Esta opción no es ganadora")

        # Calcular shares netos (compras - ventas - redenciones)
        compras = (
            TransaccionShare.objects.filter(usuario=usuario, opcion=opcion, tipo="compra")
            .aggregate(t=Sum("shares"))["t"] or Decimal(0)
        )
        ventas = (
            TransaccionShare.objects.filter(usuario=usuario, opcion=opcion, tipo="venta")
            .aggregate(t=Sum("shares"))["t"] or Decimal(0)
        )
        redenciones = (
            TransaccionShare.objects.filter(usuario=usuario, opcion=opcion, tipo="redencion")
            .aggregate(t=Sum("shares"))["t"] or Decimal(0)
        )

        shares_netos = compras - ventas - redenciones
        if shares_netos <= 0:
            raise ValueError("No tienes shares ganadores pendientes de redimir")

        # 1 share ganador = 1 unidad de saldo
        monto = shares_netos
        
        # Agregar saldo al usuario
        usuario.saldo += monto
        usuario.save(update_fields=["saldo"])

        # Registrar transacción de redención
        TransaccionShare.objects.create(
            usuario=usuario,
            opcion=opcion,
            tipo="redencion",
            shares=shares_netos,
            monto=monto,
            precio_unitario=Decimal("1"),
        )

        return {"shares": float(shares_netos), "monto": float(monto)}