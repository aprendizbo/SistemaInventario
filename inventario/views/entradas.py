from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from ..models import (
    EntradaInventario,
    MovimientoInventario,
    Producto,
    StockUbicacion,
    Ubicacion,
)

@login_required
def registrar_entrada(request):
    productos = Producto.objects.order_by('descripcion')
    ubicaciones = Ubicacion.objects.filter(activa=True).order_by('rack', 'espacio', 'nivel')

    if request.method == 'POST':
        producto_id = request.POST.get('producto')
        cantidad = request.POST.get('cantidad')
        ubicacion_id = request.POST.get('ubicacion')
        motivo = request.POST.get('motivo', '').strip()
        observacion = request.POST.get('observacion', '').strip()

        # Validaciones
        if not producto_id:
            messages.error(request, 'Debe seleccionar un producto.')
            return redirect('inventario:registrar_entrada')

        if not cantidad:
            messages.error(request, 'Debe indicar una cantidad.')
            return redirect('inventario:registrar_entrada')

        if not ubicacion_id:
            messages.error(request, 'Debe seleccionar la ubicación donde ingresará el producto.')
            return redirect('inventario:registrar_entrada')

        try:
            cantidad = int(cantidad)
        except (TypeError, ValueError):
            messages.error(request, 'La cantidad debe ser un número válido.')
            return redirect('inventario:registrar_entrada')

        if cantidad <= 0:
            messages.error(request, 'La cantidad debe ser mayor que cero.')
            return redirect('inventario:registrar_entrada')

        # Obtener instancias
        producto = get_object_or_404(Producto, pk=producto_id)
        ubicacion = get_object_or_404(Ubicacion, pk=ubicacion_id, activa=True)

        with transaction.atomic():
            
            # Bloquear la fila del producto para evitar condiciones de carrera
            producto = Producto.objects.select_for_update().get(pk=producto.pk)
            stock_anterior = producto.stock_teorico

            # Bloquear o crear la relación Stock-Ubicación
            stock_ubicacion, _ = StockUbicacion.objects.select_for_update().get_or_create(
                producto=producto,
                ubicacion=ubicacion,
                defaults={'cantidad': 0}
            )

            # 1. Actualizar el stock en esa ubicación específica
            stock_ubicacion.cantidad += cantidad
            stock_ubicacion.save(update_fields=['cantidad', 'fecha_actualizacion'])

            # 2. Actualizar el stock teórico total del producto
            producto.stock_teorico += cantidad
            producto.save(update_fields=['stock_teorico'])

            # 3. Registrar el log de la entrada
            EntradaInventario.objects.create(
                producto=producto,
                cantidad=cantidad,
                ubicacion=ubicacion,
                motivo=motivo,
                observacion=observacion,
                usuario=request.user,
            )

            # Stock después del movimiento
            stock_posterior = producto.stock_teorico

            # 4. Registrar en el historial de movimientos (Kardex)
            MovimientoInventario.objects.create(
                producto=producto,
                tipo='ENTRADA',
                cantidad=cantidad,
                stock_anterior=stock_anterior,
                stock_posterior=stock_posterior,
                ubicacion=ubicacion,
                ubicacion_origen=None,
                ubicacion_destino=ubicacion,
                motivo=motivo,
                observacion=observacion,
                usuario=request.user,
            )

        # Mensaje de éxito
        messages.success(
            request,
            f'Entrada registrada correctamente. '
            f'Se agregaron {cantidad} unidades de '
            f'{producto.descripcion} en {ubicacion}.'
        )

        return redirect('inventario:registrar_entrada')

    # Respuesta GET
    return render(
        request,
        'inventario/registrar_entrada.html',
        {
            'productos': productos,
            'ubicaciones': ubicaciones,
        }
    )