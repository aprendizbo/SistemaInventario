from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.contrib import messages

from ..models import SesionInventario, LogAuditoria, BaseInventario
from .bases import get_client_ip

@login_required
def panel_sesiones(request):
    sesiones = SesionInventario.objects.all().order_by('-id')

    return render(
        request,
        'inventario/panel_sesiones.html',
        {
            'sesiones': sesiones
        }
    )

@login_required
@require_POST
def crear_sesion(request):
    nombre = request.POST.get('nombre_sesion')

    # ============================================================
    # BUSCAR LA BASE DE INVENTARIO ACTIVA
    # ============================================================

    base_activa = BaseInventario.objects.filter(
        estado='ACTIVA'
    ).order_by('-id').first()

    if not base_activa:
        messages.error(
            request,
            'No existe una Base de Inventario activa. '
            'Debe crear una base antes de abrir una sesión.'
        )
        return redirect('inventario:panel_sesiones')

    # ============================================================
    # NOMBRE AUTOMÁTICO
    # ============================================================

    if not nombre:
        fecha_str = timezone.now().strftime("%Y-%m-%d %H:%M")
        nombre = f"Inventario General - {fecha_str}"

    # ============================================================
    # CREAR SESIÓN ASOCIADA A LA BASE ACTIVA
    # ============================================================

    sesion = SesionInventario.objects.create(
        nombre=nombre,
        estado='ABIERTA',
        creado_por=request.user,
        base=base_activa
    )

    # ============================================================
    # AUDITORÍA
    # ============================================================

    LogAuditoria.objects.create(
        usuario=request.user,
        accion='CREAR',
        modelo='SesionInventario',
        objeto_id=str(sesion.id),
        descripcion=(
            f"Apertura de nueva sesión de inventario: "
            f"{sesion.nombre}. "
            f"Base asociada: {base_activa.nombre}"
        ),
        ip_direccion=get_client_ip(request)
    )

    messages.success(
        request,
        f'Sesión "{sesion.nombre}" creada correctamente '
        f'en la base "{base_activa.nombre}".'
    )

    return redirect('inventario:panel_sesiones')

@login_required
def cerrar_sesion(request, sesion_id):
    sesion = get_object_or_404(
        SesionInventario,
        id=sesion_id
    )

    sesion.estado = 'CERRADA'
    sesion.fecha_fin = timezone.now()
    sesion.save()

    LogAuditoria.objects.create(
        usuario=request.user,
        accion='MODIFICAR',
        modelo='SesionInventario',
        objeto_id=str(sesion.id),
        descripcion=f"Cierre de sesión de inventario: {sesion.nombre}",
        ip_direccion=get_client_ip(request)
    )

    return redirect('inventario:panel_sesiones')

@login_required
def eliminar_sesion(request, sesion_id):
    if not request.user.is_superuser:
        messages.error(
            request,
            "No tiene permisos para realizar esta acción."
        )
        return redirect('inventario:panel_sesiones')

    sesion = get_object_or_404(
        SesionInventario,
        id=sesion_id
    )

    nombre_sesion = sesion.nombre

    LogAuditoria.objects.create(
        usuario=request.user,
        accion='ELIMINAR',
        modelo='SesionInventario',
        objeto_id=str(sesion.id),
        descripcion=f'Se eliminó la sesión "{nombre_sesion}"',
        ip_direccion=get_client_ip(request)
    )

    sesion.delete()

    messages.success(
        request,
        f'Sesión "{nombre_sesion}" eliminada correctamente.'
    )

    return redirect('inventario:panel_sesiones')