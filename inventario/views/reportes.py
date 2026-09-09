import csv
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, models
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..models import (
    BaseInventario,
    SesionInventario,
    Producto,
    ConteoDetalle,
    HistorialProducto,
    LogAuditoria,
)
from .bases import get_client_ip


# ============================================================
# EXPORTAR CONTEO DE UNA SESIÓN (Se mantiene por sesión)
# ============================================================
@login_required
def exportar_conteo_csv(request, sesion_id):
    sesion = get_object_or_404(SesionInventario.objects.select_related('base', 'creado_por'), id=sesion_id)
    
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="sesion_{sesion.id}_conteo.csv"'
    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'ID Sesion', 'Nombre Sesion', 'Base', 'Estado Sesion', 'Usuario',
        'Codigo de Barras', 'Descripcion', 'Stock Sistema', 'Cantidad Contada', 'Diferencia', 'Fecha Conteo'
    ])

    conteos = ConteoDetalle.objects.filter(sesion=sesion).select_related('producto', 'usuario').order_by('producto__descripcion')
    for item in conteos:
        diferencia = item.cantidad - item.producto.stock_teorico
        writer.writerow([
            sesion.id, sesion.nombre, sesion.base.nombre if sesion.base else '', sesion.get_estado_display(),
            item.usuario.username, item.producto.codigo_barras, item.producto.descripcion,
            item.producto.stock_teorico, item.cantidad, diferencia, item.fecha_conteo.strftime('%Y-%m-%d %H:%M:%S')
        ])

    LogAuditoria.objects.create(
        usuario=request.user, accion='EXPORTAR', modelo='ConteoDetalle', objeto_id=str(sesion.id),
        descripcion=f'Exportación CSV del conteo de la sesión "{sesion.nombre}".', ip_direccion=get_client_ip(request)
    )
    return response


# ============================================================
# LÓGICA CORE: CONSTRUIR MATRIZ DE CONCILIACIÓN
# ============================================================
def construir_conciliacion_base(base):
    sesiones = list(SesionInventario.objects.filter(base=base).select_related('creado_por').order_by('fecha_inicio'))
    
    # 1. Agrupar conteos: producto_id -> sesion_id -> cantidad total
    conteos_db = ConteoDetalle.objects.filter(sesion__base=base).values('producto_id', 'sesion_id').annotate(total=Sum('cantidad'))
    matriz = defaultdict(dict)
    for c in conteos_db: matriz[c['producto_id']][c['sesion_id']] = c['total'] or 0

    # 2. Obtener productos (los que tienen stock o fueron contados)
    productos = Producto.objects.select_related('ubicacion').filter(
        models.Q(stock_teorico__gt=0) | models.Q(id__in=matriz.keys())
    ).distinct().order_by('descripcion')

    resultados = []
    for prod in productos:
        conteos_prod = matriz.get(prod.id, {})
        sesiones_info = []
        cantidades_validas = []

        # Estructurar conteos por sesión (compatible con conciliacion_base.html)
        for s in sesiones:
            cant = conteos_prod.get(s.id)
            dif = (cant - prod.stock_teorico) if cant is not None else None
            sesiones_info.append({'sesion': s, 'cantidad': cant, 'diferencia': dif})
            if cant is not None: cantidades_validas.append(cant)

        # 3. Determinar Consenso (Mínimo 2 coincidencias idénticas)
        frecuencias = defaultdict(int)
        for c in cantidades_validas: frecuencias[c] += 1
        
        conteo_consensuado = None
        max_freq = 0
        for cant, freq in frecuencias.items():
            if freq >= 2 and freq > max_freq:
                max_freq, conteo_consensuado = freq, cant

        # 4. Asignar Estado
        if conteo_consensuado is not None: estado = 'CONSENSO'
        elif not cantidades_validas: estado = 'SIN_CONTEO'
        elif len(cantidades_validas) == 1: estado = 'UN_SOLO_CONTEO'
        else: estado = 'DIFERENCIA'

        dif_sistema = (conteo_consensuado - prod.stock_teorico) if conteo_consensuado is not None else None

        resultados.append({
            'producto': prod,
            'stock_sistema': prod.stock_teorico,
            'sesiones': sesiones_info,  # Usado por la plantilla
            'conteo_consensuado': conteo_consensuado,
            'diferencia_sistema': dif_sistema,
            'estado': estado
        })

    return sesiones, resultados


# ============================================================
# VISTA: VER TABLA DE CONCILIACIÓN DE BASE
# ============================================================
@login_required
def conciliacion_base(request, base_id):
    base = get_object_or_404(BaseInventario, id=base_id)
    sesiones, resultados = construir_conciliacion_base(base)

    if not sesiones:
        messages.warning(request, f'La base "{base.nombre}" aún no tiene sesiones de inventario.')

    return render(request, 'inventario/conciliacion_base.html', {
        'base': base,
        'sesiones': sesiones,
        'resultados': resultados,
    })


# ============================================================
# VISTA: APLICAR CONCILIACIÓN FINAL AL MAESTRO
# ============================================================
@login_required
@require_POST
def aplicar_conciliacion_base(request, base_id):
    base = get_object_or_404(BaseInventario, id=base_id)

    if base.estado != 'ACTIVA' or base.conciliacion_aplicada:
        messages.error(request, 'La base no está activa o ya fue conciliada.')
        return redirect('inventario:conciliacion_base', base_id=base.id)

    sesiones, resultados = construir_conciliacion_base(base)

    # Validaciones de integridad
    if len(sesiones) < 2 or any(s.estado == 'ABIERTA' for s in sesiones):
        messages.error(request, 'No se puede conciliar: Deben existir al menos 2 sesiones y TODAS deben estar CERRADAS.')
        return redirect('inventario:conciliacion_base', base_id=base.id)

    if any(r['conteo_consensuado'] is None for r in resultados):
        messages.error(request, 'Todos los productos mostrados deben alcanzar un estado de CONSENSO para poder aplicar.')
        return redirect('inventario:conciliacion_base', base_id=base.id)

    try:
        with transaction.atomic():
            for item in resultados:
                prod, cant, dif = item['producto'], item['conteo_consensuado'], item['diferencia_sistema']

                # 1. Respaldar en Historial
                ub = prod.ubicacion
                HistorialProducto.objects.update_or_create(
                    base=base, codigo_barras=prod.codigo_barras,
                    defaults={
                        'descripcion': prod.descripcion, 'stock_teorico': prod.stock_teorico,
                        'rack': ub.rack if ub else '', 'espacio': ub.espacio if ub else '', 'nivel': ub.nivel if ub else '',
                        'cantidad_contada': cant, 'diferencia': dif
                    }
                )

                # 2. Actualizar Maestro
                prod.stock_teorico = cant
                prod.save(update_fields=['stock_teorico'])

            # 3. Cerrar Base y Marcar
            base.conciliacion_aplicada = True
            base.fecha_conciliacion = timezone.now()
            base.conciliado_por = request.user
            base.estado = 'CERRADA'
            base.save(update_fields=['conciliacion_aplicada', 'fecha_conciliacion', 'conciliado_por', 'estado'])

            # 4. Auditar
            LogAuditoria.objects.create(
                usuario=request.user, accion='AJUSTE', modelo='BaseInventario', objeto_id=str(base.id),
                descripcion=f'Conciliación aplicada a la base "{base.nombre}". Productos: {len(resultados)}.',
                ip_direccion=get_client_ip(request)
            )

        messages.success(request, f'Conciliación de "{base.nombre}" aplicada con éxito. {len(resultados)} productos actualizados.')

    except Exception as e:
        messages.error(request, f'Error crítico al aplicar: {str(e)}')

    return redirect('inventario:bases_productos')