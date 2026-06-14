from django.urls import path
from . import views
from . import views_ruleta

urlpatterns = [
    # Páginas
    path('', views.home, name='home'),
    path('mercado/<int:mercado_id>/', views.mercado_detalle, name='mercado_detalle'),
    path('portafolio/<int:id_usuario>/', views.portafolio_page, name='portafolio_page'),

    # APIs JSON
    path('mercados/', views.lista_mercados, name='mercados'),
    path('comprar/', views.comprar_view, name='comprar'),
    path('vender/', views.vender_view, name='vender'),
    path('redimir/', views.redimir_view, name='redimir'),
    path('api/racha/canjear/', views.canjear_racha_view, name='canjear_racha'),
    path('api/mercado/<int:mercado_id>/', views.mercado_api, name='mercado_api'),
    path('api/mercado/<int:mercado_id>/historial/', views.historial_precios_api, name='historial_precios'),
    path('api/mercado/<int:mercado_id>/resolver/', views.resolver_view, name='resolver'),
    path('api/portafolio/<int:id_usuario>/', views.portafolio, name='portafolio_api'),
    path('api/usuario/<int:id_usuario>/', views.usuario_api, name='usuario_api'),
    path('api/historial/<int:id_usuario>/', views.historial_usuario_api, name='historial_usuario'),
    path('registro/', views.registro_view, name='registro'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('perfil/', views.perfil_view, name='perfil'),
    
    # Ruleta y Coleccionables
    path('ruleta/modal/', views_ruleta.ruleta_modal_view, name='ruleta_modal'),
    path('ruleta/comprar-giro/', views_ruleta.comprar_giro_view, name='comprar_giro'),
    path('ruleta/girar/', views_ruleta.girar_ruleta_view, name='girar_ruleta'),
    path('coleccionables/', views_ruleta.mis_coleccionables_view, name='mis_coleccionables'),
]
