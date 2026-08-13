import csv
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from ..models import (
    SesionInventario,
    Producto,
    ConteoDetalle,
    LogAuditoria,
)

from .bases import get_client_ip


# ============================================================
# EXPORTAR CONTEO DE UNA SESIÓN
# ============================================================

@login_required
def exportar_conteo_csv(request, sesion_id):

    sesion = get_object_or_404(
        SesionInventario,
        id=sesion_id
    )

    LogAuditoria.objects.create(
        usuario=request.user,
        accion='EXPORTAR',
        modelo='ConteoDetalle',
        objeto_id=str(sesion.id),
        descripcion=(
            f"Exportación CSV sesión: {sesion.nombre}"
        ),
        ip_direccion=get_client_ip(request)
    )

    response = HttpResponse(
        content_type='text/csv; charset=utf-8'
    )

    response['Content-Disposition'] = (
        f'attachment; filename="historial_sesion_{sesion_id}.csv"'
    )

    writer = csv.writer(response)

    writer.writerow([
        'ID Sesion',
        'Nombre Sesion',
        'Codigo de Barras',
        'Descripcion',
        'Stock Teorico',
        'Cantidad',
        'Operario',
        'Fecha Conteo',
    ])

    conteos = ConteoDetalle.objects.filter(
        sesion=sesion
    ).select_related(
        'producto',
        'usuario'
    )

    for item in conteos:

        writer.writerow([
            sesion.id,
            sesion.nombre,
            item.producto.codigo_barras,
            item.producto.descripcion,
            item.producto.stock_teorico,
            item.cantidad,
            item.usuario.username,
            item.fecha_conteo.strftime(
                '%Y-%m-%d %H:%M:%S'
            ),
        ])

    return response


# ============================================================
# CONCILIACIÓN DE UNA SESIÓN
# ============================================================

@login_required
def conciliacion_sesion(request, sesion_id):

    sesion = get_object_or_404(
        SesionInventario,
        id=sesion_id
    )

    productos = Producto.objects.select_related(
        'ubicacion'
    ).all()

    resultados = []

    for producto in productos:

        cantidad_escaneada = (
            producto.conteos
            .filter(sesion=sesion)
            .aggregate(
                total=Sum('cantidad')
            )['total']
            or 0
        )

        diferencia = (
            cantidad_escaneada -
            producto.stock_teorico
        )

        if (
            cantidad_escaneada > 0
            or producto.stock_teorico > 0
        ):
            resultados.append({
                'producto': producto,
                'stock_teorico': producto.stock_teorico,
                'cantidad_escaneada': cantidad_escaneada,
                'diferencia': diferencia,
            })

    return render(
        request,
        'inventario/conciliacion.html',
        {
            'sesion': sesion,
            'resultados': resultados,
        }
    )


# ============================================================
# APLICAR AJUSTE DEL INVENTARIO
# ============================================================

@login_required
@require_POST
def aplicar_ajuste_inventario(request, sesion_id):
    """
    Aplica el resultado de una sesión de inventario
    al maestro de productos.

    Una sesión solo puede aplicarse una vez.
    El proceso completo se ejecuta dentro de una transacción.
    """

    sesion = get_object_or_404(
        SesionInventario,
        id=sesion_id
    )

    # ============================================================
    # 1. VALIDAR ESTADO DE LA SESIÓN
    # ============================================================

    if sesion.estado == 'CERRADA':
        messages.error(
            request,
            'Esta sesión ya fue cerrada y no puede volver a aplicarse.'
        )

        return redirect(
            'inventario:conciliacion',
            sesion_id=sesion.id
        )

    # ============================================================
    # 2. APLICAR EL INVENTARIO DENTRO DE UNA TRANSACCIÓN
    # ============================================================

    try:

        with transaction.atomic():

            productos = Producto.objects.select_related(
                'ubicacion'
            ).all()

            productos_actualizados = 0

            # ====================================================
            # 3. RECORRER EL MAESTRO
            # ====================================================

            for producto in productos:

                cantidad_escaneada = (
                    producto.conteos
                    .filter(sesion=sesion)
                    .aggregate(
                        total=Sum('cantidad')
                    )['total'] or 0
                )

                # =================================================
                # Si el producto fue contado, actualizar stock.
                #
                # Si NO fue contado, NO modificamos su stock.
                # Esto es importante para inventarios parciales.
                # =================================================

                if cantidad_escaneada > 0:

                    producto.stock_teorico = cantidad_escaneada
                    producto.save(
                        update_fields=['stock_teorico']
                    )

                    productos_actualizados += 1

            # ====================================================
            # 4. CERRAR LA SESIÓN
            # ====================================================

            sesion.estado = 'CERRADA'
            sesion.fecha_fin = timezone.now()

            sesion.save(
                update_fields=[
                    'estado',
                    'fecha_fin'
                ]
            )

            # ====================================================
            # 5. AUDITORÍA
            # ====================================================

            LogAuditoria.objects.create(
                usuario=request.user,
                accion='AJUSTE',
                modelo='SesionInventario',
                objeto_id=str(sesion.id),
                descripcion=(
                    f"Se aplicó el inventario de la sesión "
                    f"'{sesion.nombre}'. "
                    f"Productos actualizados: "
                    f"{productos_actualizados}."
                ),
                ip_direccion=get_client_ip(request)
            )

        # ========================================================
        # 6. MENSAJE FINAL
        # ========================================================

        messages.success(
            request,
            (
                f'La sesión "{sesion.nombre}" fue aplicada '
                f'correctamente. '
                f'Se actualizaron {productos_actualizados} productos.'
            )
        )

    except Exception as e:

        messages.error(
            request,
            (
                'No fue posible aplicar el inventario. '
                f'No se realizaron cambios. Error: {str(e)}'
            )
        )

    return redirect(
        'inventario:panel_sesiones'
    )