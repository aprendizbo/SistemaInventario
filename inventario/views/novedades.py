from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F

from ..models import (
    Novedad,
    Producto,
    ConteoDetalle,
    LogAuditoria,
)
from ..forms import ProductoForm

# Importamos la función auxiliar desde bases.py
from .bases import get_client_ip


@login_required
def lista_novedades(request):
    novedades = Novedad.objects.select_related(
        'sesion',
        'usuario'
    ).all().order_by('-id')

    return render(
        request,
        'inventario/novedades.html',
        {
            'novedades': novedades
        }
    )


@login_required
def asociar_novedad(request, novedad_id):
    novedad = get_object_or_404(
        Novedad,
        id=novedad_id
    )

    if request.method == 'POST':
        producto_id = request.POST.get('producto_id')

        if producto_id:
            producto = get_object_or_404(
                Producto,
                id=producto_id
            )

            codigo_viejo = producto.codigo_barras
            producto.codigo_barras = novedad.codigo_barras_detectado
            producto.save()

            conteo, created = ConteoDetalle.objects.get_or_create(
                sesion=novedad.sesion,
                producto=producto,
                usuario=novedad.usuario,
                defaults={
                    'cantidad': novedad.cantidad
                }
            )

            if not created:
                ConteoDetalle.objects.filter(
                    id=conteo.id
                ).update(
                    cantidad=F('cantidad') + novedad.cantidad
                )

            novedad.delete()

            LogAuditoria.objects.create(
                usuario=request.user,
                accion='CONCILIAR',
                modelo='Producto',
                objeto_id=str(producto.id),
                descripcion=(
                    f"Novedad resuelta. Código "
                    f"'{codigo_viejo}' actualizado a "
                    f"'{producto.codigo_barras}' para el "
                    f"producto '{producto.descripcion}'"
                ),
                ip_direccion=get_client_ip(request)
            )

            messages.success(
                request,
                f"¡Éxito! Código asignado a '{producto.descripcion}' y conteo consolidado."
            )

            return redirect('inventario:lista_novedades')

    productos = Producto.objects.all().order_by('descripcion')

    return render(
        request,
        'inventario/asociar_novedad.html',
        {
            'novedad': novedad,
            'productos': productos
        }
    )


@login_required
def crear_desde_novedad(request, novedad_id):
    novedad = get_object_or_404(
        Novedad,
        id=novedad_id
    )

    if request.method == 'POST':
        form = ProductoForm(request.POST)

        if form.is_valid():
            nuevo_producto = form.save()

            conteo, created = ConteoDetalle.objects.get_or_create(
                sesion=novedad.sesion,
                producto=nuevo_producto,
                usuario=novedad.usuario,
                defaults={
                    'cantidad': novedad.cantidad
                }
            )

            if not created:
                ConteoDetalle.objects.filter(
                    id=conteo.id
                ).update(
                    cantidad=F('cantidad') + novedad.cantidad
                )

            novedad.delete()

            LogAuditoria.objects.create(
                usuario=request.user,
                accion='CREAR',
                modelo='Producto',
                objeto_id=str(nuevo_producto.id),
                descripcion=(
                    f"Resolución de novedad. Creó producto nuevo: "
                    f"{nuevo_producto.codigo_barras} - "
                    f"{nuevo_producto.descripcion}"
                ),
                ip_direccion=get_client_ip(request)
            )

            messages.success(
                request,
                f"¡Ficha creada! Producto '{nuevo_producto.descripcion}' registrado con conteo asociado."
            )

            return redirect('inventario:lista_novedades')

    else:
        form = ProductoForm(
            initial={
                'codigo_barras': novedad.codigo_barras_detectado,
                'stock_teorico': 0
            }
        )

    return render(
        request,
        'inventario/crear_desde_novedad.html',
        {
            'form': form,
            'novedad': novedad
        }
    )