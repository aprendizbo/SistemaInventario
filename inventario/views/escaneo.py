import json

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from ..models import (
    SesionInventario,
    Producto,
    ConteoDetalle,
    Novedad,
    LogAuditoria,
)


@login_required
def pantalla_escaner(request, sesion_id):
    sesion = get_object_or_404(
        SesionInventario.objects.select_related('base'),
        id=sesion_id,
        estado='ABIERTA'
    )

    recientes = (
        ConteoDetalle.objects
        .filter(sesion=sesion)
        .select_related(
            'producto',
            'producto__ubicacion'
        )
        .order_by('-id')[:5]
    )

    return render(
        request,
        'inventario/escaner.html',
        {
            'sesion': sesion,
            'recientes': recientes,
        }
    )


@login_required
@require_POST
def procesar_escaneo(request):

    # ==========================================================
    # 1. RECIBIR Y VALIDAR DATOS
    # ==========================================================

    try:
        data = json.loads(request.body)

        codigo = str(
            data.get('codigo_barras', '')
        ).strip()

        sesion_id = data.get('sesion_id')

        cantidad_ingresada = int(
            data.get('cantidad', 1)
        )

    except (
        json.JSONDecodeError,
        AttributeError,
        ValueError,
        TypeError,
    ):
        return JsonResponse(
            {
                'status': 'error',
                'message': 'Datos inválidos.',
            },
            status=400
        )

    if not codigo:
        return JsonResponse(
            {
                'status': 'error',
                'message': 'Debe proporcionar un código de barras.',
            },
            status=400
        )

    if not sesion_id:
        return JsonResponse(
            {
                'status': 'error',
                'message': 'No se recibió la sesión de inventario.',
            },
            status=400
        )

    if cantidad_ingresada <= 0:
        return JsonResponse(
            {
                'status': 'error',
                'message': 'La cantidad debe ser mayor a 0.',
            },
            status=400
        )

    # ==========================================================
    # 2. VALIDAR SESIÓN
    # ==========================================================

    sesion = get_object_or_404(
        SesionInventario.objects.select_related('base'),
        id=sesion_id,
        estado='ABIERTA'
    )

    if not sesion.base_id:
        return JsonResponse(
            {
                'status': 'error',
                'message': (
                    'La sesión no tiene una Base de Inventario asociada.'
                ),
            },
            status=400
        )

    # ==========================================================
    # 3. BUSCAR PRODUCTO
    # ==========================================================

    try:
        producto = (
            Producto.objects
            .select_related('ubicacion')
            .get(codigo_barras=codigo)
        )

    except Producto.DoesNotExist:

        # ------------------------------------------------------
        # CÓDIGO NO REGISTRADO → NOVEDAD
        # ------------------------------------------------------

        try:
            with transaction.atomic():

                novedad = (
                    Novedad.objects
                    .select_for_update()
                    .filter(
                        sesion=sesion,
                        codigo_barras_detectado=codigo,
                        motivo='NO_EXISTE',
                    )
                    .first()
                )

                if novedad:
                    novedad.cantidad = (
                        F('cantidad') + cantidad_ingresada
                    )
                    novedad.usuario = request.user

                    novedad.save(
                        update_fields=[
                            'cantidad',
                            'usuario',
                        ]
                    )

                    novedad.refresh_from_db()

                else:
                    novedad = Novedad.objects.create(
                        sesion=sesion,
                        codigo_barras_detectado=codigo,
                        motivo='NO_EXISTE',
                        usuario=request.user,
                        cantidad=cantidad_ingresada,
                    )

                LogAuditoria.objects.create(
                    usuario=request.user,
                    accion='CREAR',
                    modelo='Novedad',
                    objeto_id=str(novedad.id),
                    descripcion=(
                        f'Escaneo de código no registrado '
                        f'[{codigo}] en la sesión '
                        f'"{sesion.nombre}". '
                        f'Cantidad acumulada: {novedad.cantidad}.'
                    ),
                    ip_direccion=get_client_ip(request),
                )

        except Exception as e:
            return JsonResponse(
                {
                    'status': 'error',
                    'message': (
                        f'No fue posible registrar la novedad: {str(e)}'
                    ),
                },
                status=500
            )

        return JsonResponse(
            {
                'status': 'novedad',
                'tipo': 'no_registrado',
                'message': (
                    f'Código [{codigo}] no encontrado. '
                    'Guardado en Novedades.'
                ),
                'codigo': codigo,
                'cantidad': novedad.cantidad,
            }
        )

    except Producto.MultipleObjectsReturned:

        return JsonResponse(
            {
                'status': 'error',
                'message': (
                    f'Inconsistencia en base de datos: '
                    f'códigos duplicados para [{codigo}].'
                ),
            },
            status=400
        )

    # ==========================================================
    # 4. CONTEO DEL PRODUCTO
    # ==========================================================

    try:

        with transaction.atomic():

            conteo = (
                ConteoDetalle.objects
                .select_for_update()
                .filter(
                    sesion=sesion,
                    producto=producto,
                )
                .first()
            )

            if conteo:

                conteo.cantidad = (
                    F('cantidad') + cantidad_ingresada
                )

                conteo.usuario = request.user

                conteo.save(
                    update_fields=[
                        'cantidad',
                        'usuario',
                    ]
                )

                conteo.refresh_from_db()

            else:

                try:
                    conteo = ConteoDetalle.objects.create(
                        sesion=sesion,
                        producto=producto,
                        cantidad=cantidad_ingresada,
                        usuario=request.user,
                    )

                except IntegrityError:

                    # Otro escaneo pudo crear el registro
                    # exactamente al mismo tiempo.
                    conteo = (
                        ConteoDetalle.objects
                        .select_for_update()
                        .get(
                            sesion=sesion,
                            producto=producto,
                        )
                    )

                    conteo.cantidad = (
                        F('cantidad') + cantidad_ingresada
                    )

                    conteo.usuario = request.user

                    conteo.save(
                        update_fields=[
                            'cantidad',
                            'usuario',
                        ]
                    )

                    conteo.refresh_from_db()

            diferencia = (
                conteo.cantidad -
                producto.stock_teorico
            )

            # --------------------------------------------------
            # AUDITORÍA
            # --------------------------------------------------

            LogAuditoria.objects.create(
                usuario=request.user,
                accion='MODIFICAR',
                modelo='ConteoDetalle',
                objeto_id=str(conteo.id),
                descripcion=(
                    f'Escaneo de producto '
                    f'[{producto.codigo_barras}] '
                    f'({producto.descripcion}) en sesión '
                    f'"{sesion.nombre}". '
                    f'Cantidad agregada: {cantidad_ingresada}. '
                    f'Total contado: {conteo.cantidad}. '
                    f'Stock teórico: {producto.stock_teorico}. '
                    f'Diferencia: {diferencia}.'
                ),
                ip_direccion=get_client_ip(request),
            )

            # --------------------------------------------------
            # RESPUESTA
            # --------------------------------------------------

            return JsonResponse(
                {
                    'status': 'ok',
                    'tipo': 'conteo',

                    'message': (
                        f'Producto: {producto.descripcion}'
                    ),

                    'producto': producto.descripcion,

                    'cantidad': conteo.cantidad,

                    'cantidad_agregada': cantidad_ingresada,

                    'codigo': producto.codigo_barras,

                    'stock_teorico': producto.stock_teorico,

                    'rack': (
                        producto.ubicacion.rack
                        if producto.ubicacion
                        else ''
                    ),

                    'espacio': (
                        producto.ubicacion.espacio
                        if producto.ubicacion
                        else ''
                    ),

                    'nivel': (
                        producto.ubicacion.nivel
                        if producto.ubicacion
                        else ''
                    ),

                    'diferencia': diferencia,
                }
            )

    except Exception as e:

        return JsonResponse(
            {
                'status': 'error',
                'message': (
                    f'No fue posible procesar el escaneo: {str(e)}'
                ),
            },
            status=500
        )


# ============================================================
# UTILIDAD
# ============================================================

def get_client_ip(request):
    """
    Obtiene la IP real del cliente cuando existe
    X-Forwarded-For; de lo contrario usa REMOTE_ADDR.
    """
    x_forwarded_for = request.META.get(
        'HTTP_X_FORWARDED_FOR'
    )

    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()

    return request.META.get('REMOTE_ADDR')