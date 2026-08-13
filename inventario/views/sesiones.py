from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.contrib import messages
from django.db import transaction

from ..models import (
    SesionInventario,
    LogAuditoria,
    BaseInventario,
)

from .bases import get_client_ip


# ============================================================
# PANEL DE SESIONES
# ============================================================

@login_required
def panel_sesiones(request):

    sesiones = (
        SesionInventario.objects
        .select_related(
            'base',
            'creado_por'
        )
        .order_by('-id')
    )

    return render(
        request,
        'inventario/panel_sesiones.html',
        {
            'sesiones': sesiones
        }
    )


# ============================================================
# CREAR SESIÓN
# ============================================================

@login_required
@require_POST
def crear_sesion(request):

    nombre = request.POST.get(
        'nombre_sesion',
        ''
    ).strip()

    # ========================================================
    # BUSCAR BASE ACTIVA
    # ========================================================

    base_activa = (
        BaseInventario.objects
        .filter(
            estado='ACTIVA'
        )
        .order_by('-id')
        .first()
    )

    if not base_activa:

        messages.error(
            request,
            (
                'No existe una Base de Inventario activa. '
                'Debe crear una base antes de abrir una sesión.'
            )
        )

        return redirect(
            'inventario:panel_sesiones'
        )

    # ========================================================
    # VALIDAR SESIÓN ABIERTA EN ESA BASE
    # ========================================================

    sesion_abierta = (
        SesionInventario.objects
        .filter(
            base=base_activa,
            estado='ABIERTA'
        )
        .order_by('-id')
        .first()
    )

    if sesion_abierta:

        messages.error(
            request,
            (
                f'Ya existe una sesión abierta para la base '
                f'"{base_activa.nombre}": '
                f'"{sesion_abierta.nombre}". '
                f'Debe finalizarla antes de abrir otra.'
            )
        )

        return redirect(
            'inventario:panel_sesiones'
        )

    # ========================================================
    # NOMBRE AUTOMÁTICO
    # ========================================================

    if not nombre:

        fecha_str = timezone.now().strftime(
            "%Y-%m-%d %H:%M"
        )

        nombre = (
            f"Inventario General - {fecha_str}"
        )

    # ========================================================
    # CREAR SESIÓN
    # ========================================================

    try:

        with transaction.atomic():

            sesion = SesionInventario.objects.create(
                nombre=nombre,
                estado='ABIERTA',
                creado_por=request.user,
                base=base_activa
            )

            # =================================================
            # AUDITORÍA
            # =================================================

            LogAuditoria.objects.create(
                usuario=request.user,
                accion='CREAR',
                modelo='SesionInventario',
                objeto_id=str(sesion.id),
                descripcion=(
                    f"Apertura de nueva sesión de inventario: "
                    f"{sesion.nombre}. "
                    f"Base asociada: "
                    f"{base_activa.nombre}."
                ),
                ip_direccion=get_client_ip(request)
            )

        messages.success(
            request,
            (
                f'Sesión "{sesion.nombre}" creada '
                f'correctamente en la base '
                f'"{base_activa.nombre}".'
            )
        )

    except Exception as e:

        messages.error(
            request,
            (
                'No fue posible crear la sesión. '
                f'Detalle: {str(e)}'
            )
        )

    return redirect(
        'inventario:panel_sesiones'
    )


# ============================================================
# CERRAR SESIÓN
# ============================================================

@login_required
@require_POST
def cerrar_sesion(request, sesion_id):

    sesion = get_object_or_404(
        SesionInventario,
        id=sesion_id
    )

    # ========================================================
    # VALIDAR QUE ESTÉ ABIERTA
    # ========================================================

    if sesion.estado == 'CERRADA':

        messages.error(
            request,
            (
                f'La sesión "{sesion.nombre}" '
                f'ya se encuentra cerrada.'
            )
        )

        return redirect(
            'inventario:panel_sesiones'
        )

    try:

        with transaction.atomic():

            sesion.estado = 'CERRADA'
            sesion.fecha_fin = timezone.now()

            sesion.save(
                update_fields=[
                    'estado',
                    'fecha_fin'
                ]
            )

            # =================================================
            # AUDITORÍA
            # =================================================

            LogAuditoria.objects.create(
                usuario=request.user,
                accion='MODIFICAR',
                modelo='SesionInventario',
                objeto_id=str(sesion.id),
                descripcion=(
                    f"Cierre de sesión de inventario: "
                    f"{sesion.nombre}."
                ),
                ip_direccion=get_client_ip(request)
            )

        messages.success(
            request,
            (
                f'Sesión "{sesion.nombre}" '
                f'cerrada correctamente.'
            )
        )

    except Exception as e:

        messages.error(
            request,
            (
                'No fue posible cerrar la sesión. '
                f'Detalle: {str(e)}'
            )
        )

    return redirect(
        'inventario:panel_sesiones'
    )


# ============================================================
# ELIMINAR SESIÓN
# ============================================================

@login_required
@require_POST
def eliminar_sesion(request, sesion_id):

    # ========================================================
    # SOLO SUPERUSUARIO
    # ========================================================

    if not request.user.is_superuser:

        messages.error(
            request,
            "No tiene permisos para realizar esta acción."
        )

        return redirect(
            'inventario:panel_sesiones'
        )

    sesion = get_object_or_404(
        SesionInventario,
        id=sesion_id
    )

    # ========================================================
    # NO PERMITIR ELIMINAR SESIONES ABIERTAS
    # ========================================================

    if sesion.estado == 'ABIERTA':

        messages.error(
            request,
            (
                'No se puede eliminar una sesión abierta. '
                'Debe cerrarla primero.'
            )
        )

        return redirect(
            'inventario:panel_sesiones'
        )

    nombre_sesion = sesion.nombre

    try:

        with transaction.atomic():

            # =================================================
            # AUDITORÍA ANTES DE ELIMINAR
            # =================================================

            LogAuditoria.objects.create(
                usuario=request.user,
                accion='ELIMINAR',
                modelo='SesionInventario',
                objeto_id=str(sesion.id),
                descripcion=(
                    f'Se eliminó la sesión '
                    f'"{nombre_sesion}".'
                ),
                ip_direccion=get_client_ip(request)
            )

            sesion.delete()

        messages.success(
            request,
            (
                f'Sesión "{nombre_sesion}" '
                f'eliminada correctamente.'
            )
        )

    except Exception as e:

        messages.error(
            request,
            (
                'No fue posible eliminar la sesión. '
                f'Detalle: {str(e)}'
            )
        )

    return redirect(
        'inventario:panel_sesiones'
    )