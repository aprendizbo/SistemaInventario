from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render

from inventario.forms import TransferenciaInventarioForm
from inventario.models import (
    TransferenciaInventario,
    StockUbicacion,
)


@login_required
def registrar_transferencia(request):

    if request.method == 'POST':

        form = TransferenciaInventarioForm(request.POST)

        if form.is_valid():

            try:
                with transaction.atomic():

                    transferencia = form.save(commit=False)
                    transferencia.usuario = request.user

                    producto = transferencia.producto
                    cantidad = transferencia.cantidad
                    origen = transferencia.ubicacion_origen
                    destino = transferencia.ubicacion_destino

                    # =====================================================
                    # VALIDACIÓN 1: CANTIDAD
                    # =====================================================

                    if cantidad <= 0:

                        form.add_error(
                            'cantidad',
                            'La cantidad a transferir debe ser mayor que cero.'
                        )

                        return render(
                            request,
                            'inventario/transferencias.html',
                            {'form': form}
                        )

                    # =====================================================
                    # VALIDACIÓN 2: ORIGEN Y DESTINO DIFERENTES
                    # =====================================================

                    if origen == destino:

                        form.add_error(
                            'ubicacion_destino',
                            'La ubicación de origen y destino deben ser diferentes.'
                        )

                        return render(
                            request,
                            'inventario/transferencias.html',
                            {'form': form}
                        )

                    # =====================================================
                    # BUSCAR STOCK DEL PRODUCTO EN EL ORIGEN
                    # =====================================================

                    stock_origen = StockUbicacion.objects.select_for_update().filter(
                        producto=producto,
                        ubicacion=origen
                    ).first()

                    # =====================================================
                    # VALIDACIÓN 3: EL PRODUCTO DEBE EXISTIR EN EL ORIGEN
                    # =====================================================

                    if not stock_origen:

                        form.add_error(
                            'ubicacion_origen',
                            'El producto no tiene stock registrado en la ubicación de origen.'
                        )

                        return render(
                            request,
                            'inventario/transferencias.html',
                            {'form': form}
                        )

                    # =====================================================
                    # VALIDACIÓN 4: STOCK SUFICIENTE EN EL ORIGEN
                    # =====================================================

                    if cantidad > stock_origen.cantidad:

                        form.add_error(
                            'cantidad',
                            f'No hay stock suficiente en la ubicación de origen. '
                            f'Stock disponible: {stock_origen.cantidad}.'
                        )

                        return render(
                            request,
                            'inventario/transferencias.html',
                            {'form': form}
                        )

                    # =====================================================
                    # DESCONTAR DEL ORIGEN
                    # =====================================================

                    stock_origen.cantidad -= cantidad
                    stock_origen.save(
                        update_fields=[
                            'cantidad',
                            'fecha_actualizacion'
                        ]
                    )

                    # =====================================================
                    # BUSCAR / CREAR STOCK EN DESTINO
                    # =====================================================

                    stock_destino, creado = StockUbicacion.objects.get_or_create(
                        producto=producto,
                        ubicacion=destino,
                        defaults={
                            'cantidad': 0
                        }
                    )

                    # =====================================================
                    # SUMAR AL DESTINO
                    # =====================================================

                    stock_destino.cantidad += cantidad
                    stock_destino.save(
                        update_fields=[
                            'cantidad',
                            'fecha_actualizacion'
                        ]
                    )

                    # =====================================================
                    # GUARDAR HISTORIAL
                    # =====================================================

                    transferencia.save()

                messages.success(
                    request,
                    'La transferencia se registró correctamente.'
                )

                return redirect(
                    'inventario:lista_transferencias'
                )

            except Exception as e:

                messages.error(
                    request,
                    f'No se pudo realizar la transferencia: {e}'
                )

    else:

        form = TransferenciaInventarioForm()

    return render(
        request,
        'inventario/transferencias.html',
        {
            'form': form
        }
    )


@login_required
def lista_transferencias(request):

    transferencias_lista = (
        TransferenciaInventario.objects
        .select_related(
            'producto',
            'ubicacion_origen',
            'ubicacion_destino',
            'usuario',
        )
        .all()
        .order_by('-id')
    )

    return render(
        request,
        'inventario/lista_transferencias.html',
        {
            'transferencias': transferencias_lista,
        }
    )