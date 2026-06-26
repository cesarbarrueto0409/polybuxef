"""
Vistas para el sistema de ruleta y coleccionables.

Todos los endpoints retornan JSON. El frontend (base.html) construye
el HTML del modal usando estos datos, por lo que cualquier cambio en
coleccionables o probabilidades se refleja automáticamente.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Sum
from decimal import Decimal

from core.services.ruleta_service import RuletaService
from core.models import Usuario, Perfil, Coleccionable, RuletaProbabilidad


# ---------------------------------------------------------------------------
# Helper privado
# ---------------------------------------------------------------------------

def _obtener_usuario(request):
    """
    Devuelve el Usuario de la plataforma asociado al User de Django.

    Si el Perfil (tabla intermedia) no existe aún lo crea junto al Usuario,
    así el flujo no se rompe para cuentas recién registradas.

    Args:
        request: HttpRequest con request.user autenticado

    Returns:
        Usuario: instancia del modelo Usuario

    Raises:
        Exception: cualquier error de BD inesperado
    """
    try:
        return request.user.perfil.usuario
    except Perfil.DoesNotExist:
        # Crea Usuario y Perfil la primera vez que el usuario accede
        usuario, _ = Usuario.objects.get_or_create(
            email=request.user.email or f'{request.user.username}@polybuxef.local',
            defaults={
                'nombre':   request.user.get_full_name() or request.user.username,
                'saldo':    Decimal('1000.00'),
                'username': request.user.username,
            },
        )
        Perfil.objects.create(user=request.user, usuario=usuario)
        return usuario


def _rareza_info():
    """
    Construye la lista de rarezas con su porcentaje real calculado desde BD.

    Itera sobre RAREZA_CHOICES del modelo Coleccionable y suma las
    probabilidades activas de cada rareza directamente desde RuletaProbabilidad.
    Así, si se agrega/elimina/renombra un coleccionable en cargar_coleccionables.py,
    el frontend recibe los datos actualizados sin tocar este archivo.

    Returns:
        list[dict]: lista de {label, color, emoji, porcentaje} ordenada por
                    rareza (comun → legendario)
    """
    # Mapa de rareza -> metadatos visuales
    META = {
        'comun':      {'color': '#95a5a6', 'emoji': '⬛'},
        'raro':       {'color': '#3498db', 'emoji': '🟦'},
        'epico':      {'color': '#9b59b6', 'emoji': '🟣'},
        'legendario': {'color': '#f39c12', 'emoji': '🟡'},
    }

    resultado = []
    for rareza, label in Coleccionable.RAREZA_CHOICES:
        # Suma de probabilidades individuales para esta rareza
        total = RuletaProbabilidad.objects.filter(
            coleccionable__rareza=rareza,
            activo=True
        ).aggregate(t=Sum('probabilidad'))['t'] or Decimal('0')

        meta = META.get(rareza, {'color': '#888', 'emoji': '⬜'})
        resultado.append({
            'rareza':     rareza,
            'label':      label,
            'color':      meta['color'],
            'emoji':      meta['emoji'],
            'porcentaje': round(float(total) * 100, 1),
        })

    return resultado


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@login_required
def ruleta_modal_view(request):
    """
    Retorna los datos necesarios para que el frontend construya el modal.

    Incluye saldo, giros, costo y la tabla de rarezas con porcentajes
    calculados en tiempo real desde la BD.

    Args:
        request: HttpRequest GET autenticado

    Returns:
        JsonResponse: {saldo, giros_disponibles, costo_giro, rarezas}
    """
    try:
        usuario = _obtener_usuario(request)
        config  = RuletaService.obtener_configuracion()

        return JsonResponse({
            'saldo':            float(usuario.saldo),
            'giros_disponibles': usuario.giros_disponibles,
            'costo_giro':       float(config.costo_giro),
            'rarezas':          _rareza_info(),   # datos dinámicos desde BD
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def comprar_giro_view(request):
    """
    Compra un giro descontando saldo al usuario.

    Args:
        request: HttpRequest POST autenticado

    Returns:
        JsonResponse:
            success=True  -> {success, giros_disponibles, saldo_restante, costo}
            success=False -> {success, error}  (400 si ValueError, 500 si error inesperado)
    """
    try:
        usuario   = _obtener_usuario(request)
        resultado = RuletaService.comprar_giros(usuario.id, 1)

        return JsonResponse({
            'success':          True,
            'giros_disponibles': resultado['giros_totales'],
            'saldo_restante':   float(resultado['saldo_restante']),
            'costo':            float(resultado['costo_total']),
        })
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception:
        return JsonResponse({'success': False, 'error': 'Error al comprar giro'}, status=500)


@login_required
@require_POST
def girar_ruleta_view(request):
    """
    Gira la ruleta y asigna un coleccionable al usuario.

    Args:
        request: HttpRequest POST autenticado

    Returns:
        JsonResponse:
            success=True  -> {success, coleccionable{...}, es_nuevo, cantidad_total, giros_restantes}
            success=False -> {success, error}
    """
    try:
        usuario   = _obtener_usuario(request)
        resultado = RuletaService.girar_ruleta(usuario.id)
        col       = resultado['coleccionable']

        return JsonResponse({
            'success': True,
            'coleccionable': {
                'id':           col.id,
                'nombre':       col.nombre,
                'descripcion':  col.descripcion,
                'imagen_url':   col.imagen_url,
                'rareza':       resultado['rareza'],
                'rareza_display': col.get_rareza_display(),
            },
            'es_nuevo':       resultado['es_nuevo'],
            'cantidad_total': resultado['cantidad_total'],
            'giros_restantes': resultado['giros_restantes'],
        })
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception:
        return JsonResponse({'success': False, 'error': 'Error al girar la ruleta'}, status=500)


@login_required
def mis_coleccionables_view(request):
    """
    Página con el inventario de coleccionables del usuario.

    Agrupa los coleccionables por rareza para facilitar el render
    en la plantilla.

    Args:
        request: HttpRequest GET autenticado

    Returns:
        HttpResponse: render de ruleta/mis_coleccionables.html
    """
    try:
        usuario  = _obtener_usuario(request)
        stats    = RuletaService.obtener_estadisticas_usuario(usuario.id)
        inventario = RuletaService.obtener_coleccionables_usuario(usuario.id)

        # Agrupar por rareza usando las claves definidas en el modelo
        coleccionables_por_rareza = {r: [] for r, _ in Coleccionable.RAREZA_CHOICES}
        for item in inventario:
            coleccionables_por_rareza[item.coleccionable.rareza].append({
                'coleccionable':  item.coleccionable,
                'cantidad':       item.cantidad,
                'fecha_obtencion': item.fecha_obtencion,
            })

        return render(request, 'ruleta/mis_coleccionables.html', {
            'usuario':                  usuario,
            'stats':                    stats,
            'coleccionables_por_rareza': coleccionables_por_rareza,
            'total_coleccionables':     stats['coleccionables_obtenidos'],
            'total_posibles':           stats['total_coleccionables'],
            'porcentaje':               stats['porcentaje_completado'],
        })
    except Exception as e:
        return render(request, 'ruleta/mis_coleccionables.html', {'error': str(e)})
