from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from ..models import (
    MovimientoInventario,
    Producto,
    SalidaInventario,
    StockUbicacion,
    Ubicacion,
)

@login_required
def registrar_salida(request):
    productos = Producto.objects.order_by('descripcion')
    ubicaciones = Ubicacion.objects.filter(activa=True).order_by('rack', 'espacio', 'nivel')

    if request.method == 'POST':
        producto_id = request.POST.get('producto')
        cantidad = request.POST.get('cantidad')
        ubicacion_id = request.POST.get('ubicacion')
        motivo = request.POST.get('motivo', '').strip()
        observacion = request.POST.get('observacion', '').strip()

        # Validaciones de campos
        if not producto_id:
            messages.error(request, 'Debe seleccionar un producto.')
            return redirect('inventario:registrar_salida')

        if not cantidad:
            messages.error(request, 'Debe indicar una cantidad.')
            return redirect('inventario:registrar_salida')

        if not ubicacion_id:
            messages.error(request, 'Debe seleccionar la ubicación de donde saldrá el producto.')
            return redirect('inventario:registrar_salida')

        try:
            cantidad = int(cantidad)
        except (TypeError, ValueError):
            messages.error(request, 'La cantidad debe ser un número válido.')
            return redirect('inventario:registrar_salida')

        if cantidad <= 0:
            messages.error(request, 'La cantidad debe ser mayor que cero.')
            return redirect('inventario:registrar_salida')

        # Obtener instancias
        producto = get_object_or_404(Producto, pk=producto_id)
        ubicacion = get_object_or_404(Ubicacion, pk=ubicacion_id, activa=True)

        with transaction.atomic():
            
            # Bloqueamos producto para evitar condiciones de carrera
            producto = Producto.objects.select_for_update().get(pk=producto.pk)

            # Buscamos y bloqueamos el stock específico en la ubicación solicitada
            stock_ubicacion = (
                StockUbicacion.objects
                .select_for_update()
                .filter(producto=producto, ubicacion=ubicacion)
                .first()
            )

            # Validaciones de existencia de stock en la ubicación y global
            if not stock_ubicacion:
                messages.error(
                    request,
                    f'El producto no tiene stock registrado en {ubicacion}.'
                )
                return redirect('inventario:registrar_salida')

            if stock_ubicacion.cantidad < cantidad:
                messages.error(
                    request,
                    f'No hay suficiente stock en {ubicacion}. '
                    f'Stock disponible en esta ubicación: {stock_ubicacion.cantidad}.'
                )
                return redirect('inventario:registrar_salida')

            if producto.stock_teorico < cantidad:
                messages.error(
                    request,
                    f'El stock total del producto es insuficiente. '
                    f'Stock disponible: {producto.stock_teorico}.'
                )
                return redirect('inventario:registrar_salida')

            # 1. Guardar stock anterior
            stock_anterior = producto.stock_teorico

            # 2. Descontar stock de la ubicación específica
            stock_ubicacion.cantidad -= cantidad
            stock_ubicacion.save(update_fields=['cantidad', 'fecha_actualizacion'])

            # 3. Descontar stock total del producto
            producto.stock_teorico -= cantidad
            producto.save(update_fields=['stock_teorico'])

            # 4. Registrar salida física
            SalidaInventario.objects.create(
                producto=producto,
                cantidad=cantidad,
                ubicacion=ubicacion,
                motivo=motivo,
                observacion=observacion,
                usuario=request.user,
            )

            stock_posterior = producto.stock_teorico

            # 5. Registrar movimiento en Kardex
            MovimientoInventario.objects.create(
                producto=producto,
                tipo='SALIDA',
                cantidad=cantidad,
                stock_anterior=stock_anterior,
                stock_posterior=stock_posterior,
                ubicacion=ubicacion,
                motivo=motivo,
                observacion=observacion,
                usuario=request.user,
            )

        # Mensaje de éxito
        messages.success(
            request,
            f'Salida registrada correctamente. '
            f'Se retiraron {cantidad} unidades de {producto.descripcion} desde {ubicacion}.'
        )

        return redirect('inventario:registrar_salida')

    # Añadimos la consulta de stocks para el contexto del GET
    stock_ubicaciones = StockUbicacion.objects.select_related(
        'producto',
        'ubicacion'
    ).filter(
        ubicacion__activa=True
    )

    return render(
        request,
        'inventario/registrar_salida.html',
        {
            'productos': productos,
            'ubicaciones': ubicaciones,
            'stock_ubicaciones': stock_ubicaciones,
        }
    )