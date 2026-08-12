import csv

from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Sum
from django.utils import timezone

from ..models import (
    SesionInventario,
    Producto,
    ConteoDetalle,
    LogAuditoria,
)

# Importamos la función auxiliar desde bases.py
from .bases import get_client_ip


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
        descripcion=f"Exportación CSV sesión: {sesion.nombre}",
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
        'Operario'
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
            item.usuario.username
        ])

    return response


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

    for p in productos:
        cantidad_escaneada = (
            p.conteos
            .filter(sesion=sesion)
            .aggregate(
                Sum('cantidad')
            )['cantidad__sum'] or 0
        )

        diferencia = (
            cantidad_escaneada -
            p.stock_teorico
        )

        if cantidad_escaneada > 0 or p.stock_teorico > 0:
            resultados.append({
                'producto': p,
                'stock_teorico': p.stock_teorico,
                'cantidad_escaneada': cantidad_escaneada,
                'diferencia': diferencia,
            })

    return render(
        request,
        'inventario/conciliacion.html',
        {
            'sesion': sesion,
            'resultados': resultados
        }
    )


@login_required
@require_POST
def aplicar_ajuste_inventario(request, sesion_id):
    sesion = get_object_or_404(
        SesionInventario,
        id=sesion_id
    )

    if sesion.estado == 'CERRADA':
        messages.error(
            request,
            "Esta sesión ya fue cerrada."
        )

        return redirect(
            'inventario:conciliacion',
            sesion_id=sesion.id
        )

    productos = Producto.objects.all()

    for p in productos:
        cantidad_escaneada = (
            p.conteos
            .filter(sesion=sesion)
            .aggregate(
                Sum('cantidad')
            )['cantidad__sum'] or 0
        )

        if cantidad_escaneada > 0 or p.stock_teorico > 0:
            p.stock_teorico = cantidad_escaneada
            p.save()

    sesion.estado = 'CERRADA'
    sesion.fecha_fin = timezone.now()
    sesion.save()

    LogAuditoria.objects.create(
        usuario=request.user,
        accion='AJUSTE',
        modelo='Producto',
        objeto_id=str(sesion.id),
        descripcion=(
            f"Ajuste general de inventario basado "
            f"en sesión: {sesion.nombre}"
        ),
        ip_direccion=get_client_ip(request)
    )

    messages.success(
        request,
        f"Inventario '{sesion.nombre}' aplicado exitosamente."
    )

    return redirect(
        'inventario:panel_sesiones'
    )