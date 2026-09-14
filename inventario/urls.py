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
    
    # Ruta de Inventario Operativo agregada
    path('operativo/', views.inventario_operativo, name='inventario_operativo'),
    
    # Ruta para distribuir stock de un producto
    path(
        'operativo/distribuir/<int:producto_id>/',
        views.distribuir_stock,
        name='distribuir_stock'
    ),
    
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
    path(
        'productos/<int:producto_id>/editar/',
        views.editar_producto,
        name='editar_producto'
    ),
    path('importar/', views.importar_productos, name='importar_productos'),
    
    path('entradas/', views.registrar_entrada, name='registrar_entrada'),
    path('salidas/', views.registrar_salida, name='registrar_salida'),
    path('kardex/', views.kardex, name='kardex'),
    path('transferencias/', views.lista_transferencias, name='lista_transferencias'),
    path('transferencias/registrar/', views.registrar_transferencia, name='registrar_transferencia'),
    
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
    # REPORTES Y CONCILIACIÓN
    # ==========================================
    path(
        'sesiones/<int:sesion_id>/exportar/',
        views.exportar_conteo_csv,
        name='exportar_conteo_csv',
    ),
    path(
        'bases/<int:base_id>/conciliacion/',
        views.conciliacion_base,
        name='conciliacion_base',
    ),
    path(
        'bases/<int:base_id>/aplicar-conciliacion/',
        views.aplicar_conciliacion_base,
        name='aplicar_conciliacion_base',
    ),

    # ==========================================
    # GESTIÓN PERSONALIZADA DE USUARIOS
    # ==========================================
    path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('usuarios/crear/', views.crear_usuario, name='crear_usuario'),

    # ==========================================
    # GESTIÓN DE UBICACIONES
    # ==========================================
    path(
        'ubicaciones/',
        views.lista_ubicaciones,
        name='lista_ubicaciones'
    ),
    path(
        'ubicaciones/crear/',
        views.crear_ubicacion,
        name='crear_ubicacion'
    ),
    path(
        'ubicaciones/<int:ubicacion_id>/editar/',
        views.editar_ubicacion,
        name='editar_ubicacion'
    ),
    path(
        'ubicaciones/<int:ubicacion_id>/toggle/',
        views.toggle_ubicacion,
        name='toggle_ubicacion'
    ),

    path('usuarios/<int:user_id>/password/', views.cambiar_password_usuario, name='cambiar_password_usuario'),
    path('usuarios/<int:user_id>/toggle/', views.toggle_usuario, name='toggle_usuario'),

    # ==========================================
    # GESTIÓN DE BASES DE INVENTARIO
    # ==========================================
    path(
        'bases/',
        views.bases_productos,
        name='bases_productos'
    ),
    path(
        'bases/crear/',
        views.crear_base_inventario,
        name='crear_base_inventario'
    ),
    path(
        'bases/cerrar/<int:base_id>/',
        views.cerrar_base_inventario,
        name='cerrar_base_inventario'
    ),
]