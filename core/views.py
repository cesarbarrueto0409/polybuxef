import json
from decimal import Decimal
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .forms import RegistroForm
from .models import HistorialPrecio, Mercado, Opcion, Perfil, TransaccionShare, Usuario
from .services import (
    canjear_racha_diaria,
    comprar,
    obtener_estado_racha,
    redimir,
    resolver_mercado,
    vender,
)


def _get_perfil_usuario(user):
    """
    Obtiene el Perfil y Usuario asociados a un User de Django.
    Si no existe el Usuario, retorna None.
    """
    try:
        perfil = Perfil.objects.select_related('usuario').get(user=user)
        return perfil
    except Perfil.DoesNotExist:
        return None


# --- Páginas HTML ---

def home(request):
    """
    Vista principal que muestra mercados y estado de racha.
    """
    if request.user.is_authenticated:
        perfil = _get_perfil_usuario(request.user)
        if perfil:
            streak = obtener_estado_racha(perfil.usuario.id)
        else:
            streak = {
                "racha_actual": 0,
                "recompensa_hoy": 0,
                "recompensa_siguiente": 100,
                "ya_cobrada_hoy": False,
                "puede_canjear": False,
                "estado_racha": "Error al cargar racha",
            }
    else:
        streak = {
            "racha_actual": 0,
            "recompensa_hoy": 0,
            "recompensa_siguiente": 100,
            "ya_cobrada_hoy": False,
            "puede_canjear": False,
            "estado_racha": "Inicia sesión para cobrar tu racha diaria",
        }
    return render(request, 'home.html', {**streak})


def mercado_detalle(request, mercado_id):
    return render(request, 'mercado_detalle.html', {'mercado_id': mercado_id})


def portafolio_page(request, id_usuario):
    """
    Renderiza la página de portafolio.
    Args:
        id_usuario: ID del Usuario (core.models.Usuario), no del Django User
    """
    return render(request, 'portafolio.html', {'id_usuario': id_usuario})


# --- APIs JSON ---

def _opcion_dict(o):
    return {
        'id': o.id,
        'nombre': o.nombre,
        'precio': float(o.precio),
        'tokens': float(o.tokens),
        'es_ganadora': o.es_ganadora,
    }


@require_GET
def lista_mercados(request):
    estado = request.GET.get('estado', 'abierto')
    qs = Mercado.objects.prefetch_related('opciones').select_related('categoria')
    if estado != 'todos':
        qs = qs.filter(estado=estado)
    data = []
    for m in qs.order_by('-fecha_creacion'):
        data.append({
            'id': m.id,
            'titulo': m.titulo,
            'descripcion': m.descripcion,
            'categoria': m.categoria.nombre,
            'estado': m.estado,
            'liquidez_total': float(m.liquidez_total),
            'fecha_cierre': m.fecha_cierre.isoformat(),
            'opciones': [_opcion_dict(o) for o in m.opciones.all()],
        })
    return JsonResponse({'mercados': data})


@require_GET
def mercado_api(request, mercado_id):
    try:
        m = Mercado.objects.prefetch_related('opciones').select_related('categoria').get(id=mercado_id)
    except Mercado.DoesNotExist:
        return JsonResponse({'error': 'Mercado no encontrado'}, status=404)
    return JsonResponse({
        'id': m.id,
        'titulo': m.titulo,
        'descripcion': m.descripcion,
        'categoria': m.categoria.nombre,
        'estado': m.estado,
        'liquidez_total': float(m.liquidez_total),
        'fecha_cierre': m.fecha_cierre.isoformat(),
        'opciones': [_opcion_dict(o) for o in m.opciones.all()],
    })


@require_GET
def historial_precios_api(request, mercado_id):
    opciones = Opcion.objects.filter(mercado_id=mercado_id)
    data = {}
    for o in opciones:
        precios = (HistorialPrecio.objects
                   .filter(opcion=o)
                   .order_by('fecha')
                   .values('precio', 'fecha'))
        data[o.nombre] = [
            {'precio': float(p['precio']), 'fecha': p['fecha'].isoformat()}
            for p in precios
        ]
    return JsonResponse({'historial': data})


@require_GET
def usuario_api(request, id_usuario):
    """
    Devuelve información del Usuario.
    Args:
        id_usuario: ID del Usuario (core.models.Usuario)
    """
    try:
        usuario = Usuario.objects.get(id=id_usuario)
    except Usuario.DoesNotExist:
        return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
    
    return JsonResponse({
        'id': usuario.id,
        'username': usuario.username,
        'nombre': usuario.nombre,
        'saldo': float(usuario.saldo),
        'giros_disponibles': usuario.giros_disponibles,
        'fecha_registro': usuario.fecha_registro.isoformat(),
    })


@csrf_exempt
@require_POST
@login_required
def canjear_racha_view(request):
    """
    Endpoint para canjear la racha diaria del usuario.
    """
    perfil = _get_perfil_usuario(request.user)
    if not perfil:
        return JsonResponse({'error': 'Perfil no encontrado'}, status=404)
    
    try:
        resultado = canjear_racha_diaria(perfil.usuario.id)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'ok': True, **resultado})


@require_GET
def portafolio(request, id_usuario):
    """
    Devuelve el portafolio de un Usuario.
    Args:
        id_usuario: ID del Usuario (core.models.Usuario)
    """
    try:
        # Verificar que el usuario existe
        usuario = Usuario.objects.get(id=id_usuario)
        
        # Obtener transacciones del usuario
        transacciones = (
            TransaccionShare.objects
            .filter(usuario=usuario)
            .select_related('opcion__mercado')
            .order_by('opcion_id', 'fecha')
        )
    except Usuario.DoesNotExist:
        return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    posiciones = {}
    for t in transacciones:
        key = t.opcion_id
        if key not in posiciones:
            posiciones[key] = {
                'opcion_id': t.opcion_id,
                'opcion_nombre': t.opcion.nombre,
                'mercado_id': t.opcion.mercado_id,
                'mercado_titulo': t.opcion.mercado.titulo,
                'mercado_estado': t.opcion.mercado.estado,
                'es_ganadora': t.opcion.es_ganadora,
                'shares': 0,
                'monto_invertido': 0,
                'monto_redimido': 0,
            }
        if t.tipo == 'compra':
            posiciones[key]['shares'] += float(t.shares)
            posiciones[key]['monto_invertido'] += float(t.monto)
        elif t.tipo == 'venta':
            posiciones[key]['shares'] -= float(t.shares)
            posiciones[key]['monto_invertido'] -= float(t.monto)
        elif t.tipo == 'redencion':
            posiciones[key]['shares'] -= float(t.shares)
            posiciones[key]['monto_redimido'] += float(t.monto)

    resultado = [p for p in posiciones.values() if p['shares'] > 0.000001 or p['monto_redimido'] > 0]
    return JsonResponse({'portafolio': resultado})


@require_GET
def historial_usuario_api(request, id_usuario):
    """
    Devuelve el historial de transacciones de un Usuario.
    Args:
        id_usuario: ID del Usuario (core.models.Usuario)
    """
    try:
        usuario = Usuario.objects.get(id=id_usuario)
        transacciones = (
            TransaccionShare.objects
            .filter(usuario=usuario)
            .select_related('opcion__mercado')
            .order_by('-fecha')[:50]
        )
        data = [
            {
                'tipo': t.tipo,
                'opcion': t.opcion.nombre,
                'mercado': t.opcion.mercado.titulo,
                'mercado_id': t.opcion.mercado_id,
                'shares': float(t.shares),
                'monto': float(t.monto),
                'precio_unitario': float(t.precio_unitario),
                'fecha': t.fecha.isoformat(),
            }
            for t in transacciones
        ]
        return JsonResponse({'historial': data})
    except Usuario.DoesNotExist:
        return JsonResponse({'error': 'Usuario no encontrado'}, status=404)





@csrf_exempt
@require_POST
def comprar_view(request):
    """
    Endpoint para comprar shares de una opción.
    Body: {id_usuario, id_opcion, monto}
    """
    try:
        body = json.loads(request.body)
        id_usuario = int(body['id_usuario'])
        id_opcion = int(body['id_opcion'])
        monto = float(body['monto'])
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        return JsonResponse({'error': f'Datos inválidos: {e}'}, status=400)
    try:
        resultado = comprar(id_usuario, id_opcion, monto)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'ok': True, **resultado})


@csrf_exempt
@require_POST
def vender_view(request):
    try:
        body = json.loads(request.body)
        id_usuario = int(body['id_usuario'])
        id_opcion = int(body['id_opcion'])
        shares = float(body['shares'])
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        return JsonResponse({'error': f'Datos inválidos: {e}'}, status=400)
    try:
        resultado = vender(id_usuario, id_opcion, shares)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'ok': True, **resultado})


@csrf_exempt
@require_POST
def resolver_view(request, mercado_id):
    try:
        body = json.loads(request.body)
        opcion_ganadora_id = int(body['opcion_ganadora_id'])
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        return JsonResponse({'error': f'Datos inválidos: {e}'}, status=400)
    try:
        resultado = resolver_mercado(mercado_id, opcion_ganadora_id)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'ok': True, **resultado})


@csrf_exempt
@require_POST
def redimir_view(request):
    try:
        body = json.loads(request.body)
        id_usuario = int(body['id_usuario'])
        id_opcion = int(body['id_opcion'])
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        return JsonResponse({'error': f'Datos inválidos: {e}'}, status=400)
    try:
        resultado = redimir(id_usuario, id_opcion)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'ok': True, **resultado})


def registro_view(request):
    """
    Vista para registrar un nuevo usuario.
    Crea: User (Django) → Perfil → Usuario (con saldo inicial)
    """
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # Crear usuario de Django
                user = form.save()
                user.email = form.cleaned_data['email']
                user.save(update_fields=['email'])
                
                # Crear Usuario de la app con saldo inicial
                usuario = Usuario.objects.create(
                    username=form.cleaned_data['username'],
                    nombre=form.cleaned_data['nombre'],
                    email=form.cleaned_data['email'],
                    saldo=Decimal("1000")
                )
                
                # Crear Perfil intermedio
                Perfil.objects.create(
                    user=user,
                    usuario=usuario
                )
            
            login(request, user)
            return redirect('home')
    else:
        form = RegistroForm()
    
    return render(request, 'registration/registro.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect(request.GET.get('next', 'home'))
        else:
            error = 'Usuario o contraseña incorrectos.'
    return render(request, 'registration/login.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def perfil_view(request):
    """
    Vista para mostrar el perfil del usuario.
    """
    perfil = _get_perfil_usuario(request.user)
    if not perfil:
        return JsonResponse({'error': 'Perfil no encontrado'}, status=404)
    
    usuario = perfil.usuario
    return render(request, 'perfil.html', {'usuario': usuario})