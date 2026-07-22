from django.urls import path
from django.contrib.auth import views as auth_views  # <-- Sistema de autenticación nativo
from . import views

app_name = 'inventario'

urlpatterns = [
    # ==========================================
    # AUTENTICACIÓN (100% Personalizada, sin /admin/)
    # ==========================================
    path('login/', auth_views.LoginView.as_view(template_name='inventario/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='inventario:login'), name='logout'),

    # Ruta para la página principal que lista los productos (Maestro global)
    path('', views.lista_productos, name='lista_productos'),
    
    # El tablero corporativo para elegir la sesión de trabajo antes de escanear
    path('sesiones/', views.panel_sesiones, name='panel_sesiones'),
    
    # ==========================================
    # GESTIÓN DE SESIONES
    # ==========================================
    path('sesiones/crear/', views.crear_sesion, name='crear_sesion'),
    path('sesiones/cerrar/<int:sesion_id>/', views.cerrar_sesion, name='cerrar_sesion'),
    path('sesiones/eliminar/<int:sesion_id>/', views.eliminar_sesion, name='eliminar_sesion'),
    
    # ==========================================
    # ADMINISTRACIÓN PROPIA (CRUD, Sincronizaciones y Auditoría)
    # ==========================================
    path('productos/crear/', views.crear_producto, name='crear_producto'),
    path('importar/', views.importar_productos, name='importar_productos'),
    path('exportar-excel/', views.exportar_excel, name='exportar_excel'),
    path('auditoria/', views.historial_auditoria, name='historial_auditoria'),
    
    # Monitor en vivo para supervisores y soporte TI
    path('novedades/', views.lista_novedades, name='lista_novedades'),
    
    # Resolver novedades en caliente
    path('novedades/<int:novedad_id>/asociar/', views.asociar_novedad, name='asociar_novedad'),
    path('novedades/<int:novedad_id>/crear-nuevo/', views.crear_desde_novedad, name='crear_desde_novedad'),
    
    # ==========================================
    # ESCANEO Y API
    # ==========================================
    # El escáner recibe de forma obligatoria el ID de la sesión en la URL
    path('escaner/<int:sesion_id>/', views.pantalla_escaner, name='pantalla_escaner'),
    
    # Ruta API para procesar el escaneo (la que sigue llamando tu fetch de JS)
    path('procesar-escaneo/', views.procesar_escaneo, name='procesar_escaneo'),

    # ==========================================
    # REPORTES, AUDITORÍA Y CONCILIACIÓN
    # ==========================================
    # Ruta encargada de compilar los datos de la sesión y disparar la descarga del CSV
    path('sesiones/<int:sesion_id>/exportar/', views.exportar_conteo_csv, name='exportar_conteo_csv'),
    
    # Ruta para ver la tabla de diferencias (Conciliación)
    path('sesiones/<int:sesion_id>/conciliacion/', views.conciliacion_sesion, name='conciliacion'),
    
    # Ruta para aplicar el ajuste al Maestro y cerrar la sesión definitivamente
    path('sesiones/<int:sesion_id>/aplicar/', views.aplicar_ajuste_inventario, name='aplicar_ajuste'),

    # ==========================================
    # GESTIÓN PERSONALIZADA DE USUARIOS
    # ==========================================
    path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('usuarios/<int:user_id>/password/', views.cambiar_password_usuario, name='cambiar_password_usuario'),
    path('usuarios/<int:user_id>/toggle/', views.toggle_usuario, name='toggle_usuario'),
]