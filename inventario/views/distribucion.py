from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from inventario.models import Producto, StockUbicacion, Ubicacion


@login_required
def distribuir_stock(request, producto_id):

    producto = get_object_or_404(Producto, id=producto_id)

    ubicaciones = (
        Ubicacion.objects
        .filter(activa=True)
        .order_by('rack', 'espacio', 'nivel')
    )

    stocks = (
        StockUbicacion.objects
        .filter(producto=producto)
        .select_related('ubicacion')
        .order_by('ubicacion__rack', 'ubicacion__espacio', 'ubicacion__nivel')
    )

    stock_distribuido = sum(stock.cantidad for stock in stocks)
    diferencia = producto.stock_teorico - stock_distribuido

    if request.method == 'POST':

        ubicacion_id = request.POST.get('ubicacion')
        cantidad_raw = request.POST.get('cantidad', '').strip()

        errores = []

        # ==========================================================
        # VALIDACIÓN 1: UBICACIÓN
        # ==========================================================
        if not ubicacion_id:
            errores.append('Debe seleccionar una ubicación.')

        # ==========================================================
        # VALIDACIÓN 2: CANTIDAD
        # ==========================================================
        try:
            cantidad = int(cantidad_raw)
        except (TypeError, ValueError):
            cantidad = 0
            errores.append('La cantidad debe ser un número entero.')

        if cantidad <= 0:
            errores.append('La cantidad debe ser mayor que cero.')

        # ==========================================================
        # VALIDACIÓN 3: UBICACIÓN VÁLIDA
        # ==========================================================
        ubicacion = None
        if ubicacion_id:
            ubicacion = Ubicacion.objects.filter(id=ubicacion_id, activa=True).first()
            if not ubicacion:
                errores.append('La ubicación seleccionada no está disponible.')

        # ==========================================================
        # VALIDACIÓN 4: NO SUPERAR STOCK TEÓRICO
        # ==========================================================
        if not errores:
            nuevo_total = stock_distribuido + cantidad
            
            if nuevo_total > producto.stock_teorico:
                exceso = nuevo_total - producto.stock_teorico
                max_permitido = max(producto.stock_teorico - stock_distribuido, 0)
                errores.append(
                    f'La distribución supera el stock teórico en {exceso} unidades. '
                    f'Solo puede distribuir {max_permitido} unidades adicionales.'
                )

        # ==========================================================
        # MOSTRAR ERRORES
        # ==========================================================
        if errores:
            for error in errores:
                messages.error(request, error)

            return render(request, 'inventario/distribuir_stock.html', {
                'producto': producto,
                'ubicaciones': ubicaciones,
                'stocks': stocks,
                'stock_distribuido': stock_distribuido,
                'diferencia': diferencia,
            })

        # ==========================================================
        # GUARDAR DISTRIBUCIÓN
        # ==========================================================
        try:
            with transaction.atomic():
                stock, creado = (
                    StockUbicacion.objects
                    .select_for_update()
                    .get_or_create(
                        producto=producto,
                        ubicacion=ubicacion,
                        defaults={'cantidad': 0}
                    )
                )

                stock.cantidad += cantidad
                stock.save(update_fields=['cantidad', 'fecha_actualizacion'])

            messages.success(request, f'Se asignaron {cantidad} unidades a {ubicacion}.')
            return redirect('inventario:distribuir_stock', producto_id=producto.id)

        except Exception as e:
            messages.error(request, f'No se pudo actualizar la distribución: {e}')

    return render(request, 'inventario/distribuir_stock.html', {
        'producto': producto,
        'ubicaciones': ubicaciones,
        'stocks': stocks,
        'stock_distribuido': stock_distribuido,
        'diferencia': diferencia,
    })