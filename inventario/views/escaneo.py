import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import F

from ..models import (
    SesionInventario,
    Producto,
    ConteoDetalle,
    Novedad,
)


@login_required
def pantalla_escaner(request, sesion_id):

    sesion = get_object_or_404(
        SesionInventario,
        id=sesion_id,
        estado='ABIERTA'
    )

    recientes = ConteoDetalle.objects.filter(
        sesion=sesion
    ).select_related(
        'producto',
        'producto__ubicacion'
    ).order_by('-id')[:5]

    return render(
        request,
        'inventario/escaner.html',
        {
            'sesion': sesion,
            'recientes': recientes
        }
    )


@login_required
@require_POST
def procesar_escaneo(request):

    try:

        data = json.loads(request.body)

        codigo = data.get('codigo_barras')

        sesion_id = data.get('sesion_id')

        cantidad_ingresada = int(
            data.get('cantidad', 1)
        )

    except (
        json.JSONDecodeError,
        AttributeError,
        ValueError
    ):

        return JsonResponse(
            {
                'status': 'error',
                'message': 'Datos inválidos.'
            },
            status=400
        )

    if not codigo or not sesion_id:

        return JsonResponse(
            {
                'status': 'error',
                'message': 'Faltan datos (código o sesión).'
            },
            status=400
        )

    sesion = get_object_or_404(
        SesionInventario,
        id=sesion_id,
        estado='ABIERTA'
    )

    try:

        producto = Producto.objects.select_related(
            'ubicacion'
        ).get(
            codigo_barras=codigo
        )

        conteo, created = ConteoDetalle.objects.get_or_create(
            sesion=sesion,
            producto=producto,
            usuario=request.user,
            defaults={
                'cantidad': cantidad_ingresada
            }
        )

        if not created:

            ConteoDetalle.objects.filter(
                id=conteo.id
            ).update(
                cantidad=F('cantidad') + cantidad_ingresada
            )

            conteo.refresh_from_db()

        return JsonResponse(
            {
                'status': 'ok',
                'tipo': 'conteo',
                'message': f'Producto: {producto.descripcion}',
                'producto': producto.descripcion,
                'cantidad': conteo.cantidad,
                'codigo': producto.codigo_barras,
                'stock_teorico': producto.stock_teorico,
                'rack': (
                    producto.ubicacion.rack
                    if producto.ubicacion else ''
                ),
                'espacio': (
                    producto.ubicacion.espacio
                    if producto.ubicacion else ''
                ),
                'nivel': (
                    producto.ubicacion.nivel
                    if producto.ubicacion else ''
                ),
                'diferencia': (
                    conteo.cantidad -
                    producto.stock_teorico
                ),
            }
        )

    except Producto.DoesNotExist:

        novedad, created = Novedad.objects.get_or_create(
            sesion=sesion,
            codigo_barras_detectado=codigo,
            motivo='NO_EXISTE',
            usuario=request.user,
            defaults={
                'cantidad': cantidad_ingresada
            }
        )

        if not created:

            Novedad.objects.filter(
                id=novedad.id
            ).update(
                cantidad=F('cantidad') + cantidad_ingresada
            )

            novedad.refresh_from_db()

        return JsonResponse(
            {
                'status': 'novedad',
                'tipo': 'no_registrado',
                'message': (
                    f'Código [{codigo}] no encontrado. '
                    'Guardado en Novedades.'
                ),
                'codigo': codigo,
                'cantidad': novedad.cantidad
            }
        )

    except Producto.MultipleObjectsReturned:

        return JsonResponse(
            {
                'status': 'error',
                'message': (
                    f'Error: Códigos duplicados para [{codigo}]'
                )
            },
            status=400
        )