import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect
from django.db import transaction
from django.db.models import Q
from .forms import RegistroForm
from .models import Perfil

from .models import Mercado, Opcion, TransaccionShare, HistorialPrecio, Usuario
from .services import (
    canjear_racha_diaria,
    comprar,
    obtener_estado_racha,
    obtener_usuario_actual,
    redimir,
    resolver_mercado,
    vender,
)


# --- Páginas HTML ---


def _usuario_desde_request(request):
    if not request.user.is_authenticated:
        return obtener_usuario_actual()

    try:
        return request.user.perfil.usuario
    except Perfil.DoesNotExist:
        usuario, _ = Usuario.objects.get_or_create(
            email=request.user.email or f'{request.user.username}@polybuxef.local',
            defaults={
                'nombre': request.user.get_full_name() or request.user.username,
                'saldo': 1000,
            },
        )
        Perfil.objects.create(user=request.user, usuario=usuario)
        return usuario


def _usuario_contexto(request):
    return {'usuario': _usuario_desde_request(request)}


def home(request):
    usuario = _usuario_desde_request(request)
    streak = obtener_estado_racha(usuario.id)
    if not request.user.is_authenticated:
        streak['puede_canjear'] = False
        streak['estado_racha'] = 'Inicia sesión para cobrar tu racha diaria'
    return render(request, 'home.html', {**streak})


def mercado_detalle(request, mercado_id):
    return render(request, 'mercado_detalle.html', {
        'mercado_id': mercado_id,
        **_usuario_contexto(request),
    })


def portafolio_page(request, id_usuario):
    return render(request, 'portafolio.html', {
        'id_usuario': id_usuario,
        **_usuario_contexto(request),
    })


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
    try:
        u = Usuario.objects.get(id=id_usuario)
    except Usuario.DoesNotExist:
        return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
    return JsonResponse({
        'id': u.id,
        'nombre': u.nombre,
        'saldo': float(u.saldo),
        'racha_actual': u.racha_actual,
        'ultima_racha': u.ultima_racha.isoformat() if u.ultima_racha else None,
    })


@require_GET
def portafolio(request, id_usuario):
    try:
        transacciones = (
            TransaccionShare.objects
            .filter(usuario_id=id_usuario)
            .select_related('opcion__mercado')
            .order_by('opcion_id', 'fecha')
        )
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
    transacciones = (
        TransaccionShare.objects
        .filter(usuario_id=id_usuario)
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


@csrf_exempt
@require_POST
@login_required
def canjear_racha_view(request):
    try:
        usuario = _usuario_desde_request(request)
        resultado = canjear_racha_diaria(usuario.id)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    resultado.pop('usuario', None)
    return JsonResponse({'ok': True, **resultado})


@csrf_exempt
@require_POST
def comprar_view(request):
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
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save()
                usuario = Usuario.objects.create(
                    nombre=form.cleaned_data['nombre'],
                    email=form.cleaned_data['email'],
                    saldo=1000,
                )
                Perfil.objects.create(user=user, usuario=usuario)
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
    perfil = request.user.perfil
    usuario = perfil.usuario
    return render(request, 'perfil.html', {'usuario': usuario})


# Busca perfiles por nombre o usuario para mostrar los resultados disponibles.
@login_required
def buscar_perfiles_view(request):
    query = request.GET.get('q', '').strip()
    perfiles = Perfil.objects.select_related('user', 'usuario').order_by('usuario__nombre')

    if query:
        perfiles = perfiles.filter(
            Q(usuario__nombre__icontains=query) |
            Q(user__username__icontains=query)
        )

    return render(request, 'buscar_perfiles.html', {
        'query': query,
        'perfiles': perfiles[:30],
    })
