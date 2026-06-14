from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from core.models import HistorialPrecio, Mercado, Opcion, Profile, Resolucion, TransaccionShare
from core.services.wallet import Wallet


def _recompensa_racha(dias):
    return min(dias, 5) * 100


def obtener_estado_racha(user_id, profile=None):
    hoy = timezone.localdate()
    if profile is None:
        profile = Profile.objects.get(user_id=user_id)

    ya_cobrada_hoy = profile.ultima_racha == hoy
    if ya_cobrada_hoy:
        racha_actual = profile.racha_actual
        recompensa_hoy = 0
        estado_racha = "Ya cobraste tu racha hoy"
    elif profile.ultima_racha == hoy - timedelta(days=1):
        racha_actual = profile.racha_actual + 1
        recompensa_hoy = _recompensa_racha(racha_actual)
        estado_racha = "Tienes una racha lista para cobrar"
    else:
        racha_actual = 1
        recompensa_hoy = _recompensa_racha(racha_actual)
        estado_racha = "Tu racha diaria te esta esperando"

    return {
        "profile": profile,
        "racha_actual": racha_actual,
        "recompensa_hoy": recompensa_hoy,
        "recompensa_siguiente": _recompensa_racha(racha_actual + 1),
        "ya_cobrada_hoy": ya_cobrada_hoy,
        "puede_canjear": not ya_cobrada_hoy,
        "estado_racha": estado_racha,
    }


def canjear_racha_diaria(user_id):
    hoy = timezone.localdate()
    recompensa_cobrada = Decimal("0")

    with transaction.atomic():
        profile = Profile.objects.select_for_update().get(user_id=user_id)
        wallet = Wallet(profile)

        if profile.ultima_racha != hoy:
            if profile.ultima_racha == hoy - timedelta(days=1):
                profile.racha_actual += 1
            else:
                profile.racha_actual = 1

            recompensa_cobrada = Decimal(_recompensa_racha(profile.racha_actual))
            wallet.grant_streak_reward(recompensa_cobrada, "Recompensa de racha diaria")
            profile.ultima_racha = hoy
            profile.save(update_fields=["racha_actual", "ultima_racha"])

    estado = obtener_estado_racha(user_id)
    estado["recompensa_cobrada"] = float(recompensa_cobrada)
    return estado


def comprar(user_id, id_opcion, monto):
    monto = Decimal(str(monto))
    with transaction.atomic():
        profile = Profile.objects.select_for_update().get(user_id=user_id)
        wallet = Wallet(profile)
        opcion = Opcion.objects.select_for_update().get(id=id_opcion)
        mercado = Mercado.objects.select_for_update().get(id=opcion.mercado_id)

        if mercado.estado != "abierto" or mercado.fecha_cierre <= timezone.now():
            raise ValueError("Mercado no disponible")
        # La validación de saldo insuficiente la hace wallet.buy_shares internamente

        opcion_contraria = (
            Opcion.objects.select_for_update()
            .exclude(id=opcion.id)
            .get(mercado=mercado)
        )

        tokens_a = opcion.tokens
        tokens_b = opcion_contraria.tokens
        k = tokens_a * tokens_b
        nuevo_tokens_b = tokens_b + monto
        nuevo_tokens_a = k / nuevo_tokens_b
        shares = tokens_a - nuevo_tokens_a
        nuevo_precio_a = nuevo_tokens_b / (nuevo_tokens_a + nuevo_tokens_b)
        precio_unitario = monto / shares

        wallet.buy_shares(monto, f"Compra opción '{opcion.nombre}' en mercado #{mercado.id}")

        opcion.tokens = nuevo_tokens_a
        opcion.precio = nuevo_precio_a
        opcion.save(update_fields=["tokens", "precio"])

        opcion_contraria.tokens = nuevo_tokens_b
        opcion_contraria.precio = 1 - nuevo_precio_a
        opcion_contraria.save(update_fields=["tokens", "precio"])

        TransaccionShare.objects.create(
            profile=profile,
            opcion=opcion,
            tipo="compra",
            shares=shares,
            monto=monto,
            precio_unitario=precio_unitario,
        )
        HistorialPrecio.objects.create(opcion=opcion, precio=nuevo_precio_a)
        HistorialPrecio.objects.create(opcion=opcion_contraria, precio=1 - nuevo_precio_a)

        mercado.liquidez_total += monto
        mercado.save(update_fields=["liquidez_total"])

        return {"shares": float(shares), "precio_unitario": float(precio_unitario)}


def vender(user_id, id_opcion, shares):
    shares = Decimal(str(shares))
    with transaction.atomic():
        profile = Profile.objects.select_for_update().get(user_id=user_id)
        wallet = Wallet(profile)
        opcion = Opcion.objects.select_for_update().get(id=id_opcion)
        mercado = Mercado.objects.select_for_update().get(id=opcion.mercado_id)

        if mercado.estado != "abierto" or mercado.fecha_cierre <= timezone.now():
            raise ValueError("Mercado no disponible")

        compras = (
            TransaccionShare.objects.filter(profile=profile, opcion=opcion, tipo="compra")
            .aggregate(t=Sum("shares"))["t"] or Decimal(0)
        )
        ventas = (
            TransaccionShare.objects.filter(profile=profile, opcion=opcion, tipo="venta")
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

        tokens_a = opcion.tokens
        tokens_b = opcion_contraria.tokens
        k = tokens_a * tokens_b
        nuevo_tokens_a = tokens_a + shares
        nuevo_tokens_b = k / nuevo_tokens_a
        monto = tokens_b - nuevo_tokens_b
        nuevo_precio_a = nuevo_tokens_b / (nuevo_tokens_a + nuevo_tokens_b)
        precio_unitario = monto / shares

        opcion.tokens = nuevo_tokens_a
        opcion.precio = nuevo_precio_a
        opcion.save(update_fields=["tokens", "precio"])

        opcion_contraria.tokens = nuevo_tokens_b
        opcion_contraria.precio = 1 - nuevo_precio_a
        opcion_contraria.save(update_fields=["tokens", "precio"])

        wallet.sell_shares(monto, f"Venta opción '{opcion.nombre}' en mercado #{mercado.id}")

        TransaccionShare.objects.create(
            profile=profile,
            opcion=opcion,
            tipo="venta",
            shares=shares,
            monto=monto,
            precio_unitario=precio_unitario,
        )
        HistorialPrecio.objects.create(opcion=opcion, precio=nuevo_precio_a)
        HistorialPrecio.objects.create(opcion=opcion_contraria, precio=1 - nuevo_precio_a)

        mercado.liquidez_total -= monto
        mercado.save(update_fields=["liquidez_total"])

        return {"monto": float(monto), "precio_unitario": float(precio_unitario)}


def resolver_mercado(mercado_id, opcion_ganadora_id):
    # Sin cambios — no toca saldo ni usuarios
    with transaction.atomic():
        mercado = Mercado.objects.select_for_update().get(id=mercado_id)
        if mercado.estado == "resuelto":
            raise ValueError("El mercado ya fue resuelto")
        if mercado.estado == "cancelado":
            raise ValueError("El mercado está cancelado")

        opcion_ganadora = Opcion.objects.get(id=opcion_ganadora_id, mercado=mercado)

        Opcion.objects.filter(mercado=mercado).update(es_ganadora=False)
        opcion_ganadora.es_ganadora = True
        opcion_ganadora.save(update_fields=["es_ganadora"])

        mercado.estado = "resuelto"
        mercado.save(update_fields=["estado"])

        Resolucion.objects.create(mercado=mercado, opcion_ganadora=opcion_ganadora)

        return {"mercado_id": mercado.id, "opcion_ganadora": opcion_ganadora.nombre}


def redimir(user_id, id_opcion):
    with transaction.atomic():
        profile = Profile.objects.select_for_update().get(user_id=user_id)
        wallet = Wallet(profile)
        opcion = Opcion.objects.select_for_update().get(id=id_opcion)

        if opcion.es_ganadora is not True:
            raise ValueError("Esta opción no es ganadora")

        compras = (
            TransaccionShare.objects.filter(profile=profile, opcion=opcion, tipo="compra")
            .aggregate(t=Sum("shares"))["t"] or Decimal(0)
        )
        ventas = (
            TransaccionShare.objects.filter(profile=profile, opcion=opcion, tipo="venta")
            .aggregate(t=Sum("shares"))["t"] or Decimal(0)
        )
        redenciones = (
            TransaccionShare.objects.filter(profile=profile, opcion=opcion, tipo="redencion")
            .aggregate(t=Sum("shares"))["t"] or Decimal(0)
        )

        shares_netos = compras - ventas - redenciones
        if shares_netos <= 0:
            raise ValueError("No tienes shares ganadores pendientes de redimir")

        monto = shares_netos
        wallet.grant_bet_reward(monto, f"Redención opción ganadora '{opcion.nombre}'")

        TransaccionShare.objects.create(
            profile=profile,
            opcion=opcion,
            tipo="redencion",
            shares=shares_netos,
            monto=monto,
            precio_unitario=Decimal("1"),
        )

        return {"shares": float(shares_netos), "monto": float(monto)}