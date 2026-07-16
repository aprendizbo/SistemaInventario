from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect # <-- Sigue siendo vital para la magia

urlpatterns = [
    path('admin/', admin.site.urls),
    path('inventario/', include('inventario.urls')),
    
    # ESTA LÍNEA ATRAPA EL ENLACE DIRECTO DEL RUNSERVER Y TE MANDA AL PANEL DE SELECCIÓN DE SESIONES
    path('', lambda request: redirect('inventario:panel_sesiones')),
]