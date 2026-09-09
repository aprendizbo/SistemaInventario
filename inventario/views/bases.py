from django.db import transaction
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum

from ..models import (
    BaseInventario,
    BaseProducto,
    Producto,
    ConteoDetalle,
    HistorialProducto,
    SesionInventario,
    LogAuditoria,
)


# ============================================================
# FUNCIONES AUXILIARES (Exportadas a otros módulos)
# ============================================================

def get_client_ip(request):
    """Obtiene la IP del cliente."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


def get_base_activa():
    """Obtiene la base de inventario actualmente activa."""
    return BaseInventario.objects.filter(estado='ACTIVA').order_by('-id').first()


# ============================================================
# LISTAR BASES DE INVENTARIO
# ============================================================

@login_required
def bases_productos(request):
    bases = BaseInventario.objects.select_related(
        'creado_por', 
        'cerrado_por'
    ).order_by('-fecha_creacion')

    return render(
        request,
        'inventario/bases_productos.html',
        {
            'bases': bases,
        }
    )


# ============================================================
# CREAR BASE DE INVENTARIO
# ============================================================

@login_required
@require_POST
def crear_base_inventario(request):

    # ============================================================
    # 1. VERIFICAR BASE ACTIVA
    # ============================================================

    base_existente = BaseInventario.objects.filter(
        estado='ACTIVA'
    ).first()

    if base_existente:
        messages.error(
            request,
            f'Ya existe una base activa: "{base_existente.nombre}". '
            f'Debe cerrarla antes de crear una nueva.'
        )
        return redirect('inventario:bases_productos')

    # ============================================================
    # 2. NOMBRE
    # ============================================================

    nombre = request.POST.get(
        'nombre_base',
        ''
    ).strip()

    if not nombre:
        fecha = timezone.now().strftime(
            '%d/%m/%Y %H:%M'
        )

        nombre = f'Base de Inventario - {fecha}'

    try:

        with transaction.atomic():

            # ====================================================
            # 3. CREAR CABECERA DE BASE
            # ====================================================

            base = BaseInventario.objects.create(
                nombre=nombre,
                estado='ACTIVA',
                creado_por=request.user
            )

            # ====================================================
            # 4. TOMAR FOTOGRAFÍA DEL MAESTRO
            # ====================================================

            productos = Producto.objects.select_related(
                'ubicacion'
            ).all()

            bases_productos = []

            for producto in productos:

                ubicacion = producto.ubicacion

                bases_productos.append(
                    BaseProducto(
                        base=base,
                        producto=producto,
                        codigo_barras=producto.codigo_barras,
                        descripcion=producto.descripcion,
                        stock_teorico=producto.stock_teorico,

                        rack=(
                            ubicacion.rack
                            if ubicacion
                            else ''
                        ),

                        espacio=(
                            ubicacion.espacio
                            if ubicacion
                            else ''
                        ),

                        nivel=(
                            ubicacion.nivel
                            if ubicacion
                            else ''
                        ),
                    )
                )

            # ====================================================
            # 5. GUARDAR SNAPSHOT
            # ====================================================

            if bases_productos:

                BaseProducto.objects.bulk_create(
                    bases_productos,
                    batch_size=500
                )

            # ====================================================
            # 6. AUDITORÍA
            # ====================================================

            LogAuditoria.objects.create(
                usuario=request.user,
                accion='CREAR',
                modelo='BaseInventario',
                objeto_id=str(base.id),
                descripcion=(
                    f'Se creó la base de inventario '
                    f'"{base.nombre}". '
                    f'Se cargaron {len(bases_productos)} '
                    f'productos como snapshot de la base.'
                ),
                ip_direccion=get_client_ip(request)
            )

        # ========================================================
        # 7. MENSAJE
        # ========================================================

        messages.success(
            request,
            (
                f'Base "{base.nombre}" creada correctamente. '
                f'Se cargaron {len(bases_productos)} productos '
                f'en la base.'
            )
        )

    except Exception as e:

        messages.error(
            request,
            f'No fue posible crear la base: {str(e)}'
        )

    return redirect(
        'inventario:bases_productos'
    )


# ============================================================
# CERRAR BASE DE INVENTARIO
# ============================================================

@login_required
@require_POST
def cerrar_base_inventario(request, base_id):

    base = get_object_or_404(
        BaseInventario,
        id=base_id,
        estado='ACTIVA'
    )

    try:
        with transaction.atomic():

            # =====================================================
            # 1. TODAS LAS SESIONES DE ESTA BASE
            # =====================================================

            sesiones = SesionInventario.objects.filter(
                base=base
            ).order_by('id')

            # No permitir cerrar la base mientras exista
            # una sesión abierta.
            sesiones_abiertas = sesiones.filter(
                estado='ABIERTA'
            ).count()

            if sesiones_abiertas > 0:
                messages.error(
                    request,
                    (
                        f'No se puede cerrar la base "{base.nombre}". '
                        f'Existen {sesiones_abiertas} sesión(es) '
                        f'abierta(s). Debe cerrarlas primero.'
                    )
                )
                return redirect('inventario:panel_sesiones')

            # =====================================================
            # 2. PRODUCTOS ACTUALES
            # =====================================================

            productos = Producto.objects.select_related(
                'ubicacion'
            ).all()

            cantidad_productos = productos.count()

            # =====================================================
            # 3. CREAR SNAPSHOT HISTÓRICO
            # =====================================================
            #
            # IMPORTANTE:
            # NO se elimina Producto.
            # NO se elimina ConteoDetalle.
            #
            # El historial guarda una fotografía del inventario
            # en el momento en que se cierra la base.
            #

            for producto in productos:

                # ========================================================
                # FOTOGRAFÍA FINAL DEL MAESTRO
                # ========================================================
                # El histórico representa el estado final del inventario
                # al momento de cerrar la base.
                #
                # NO se suman los conteos de las diferentes sesiones,
                # porque cada sesión es un conteo independiente.
                # ========================================================

                cantidad_contada = producto.stock_teorico

                diferencia = 0

                HistorialProducto.objects.create(
                    base=base,
                    codigo_barras=producto.codigo_barras,
                    descripcion=producto.descripcion,
                    stock_teorico=producto.stock_teorico,

                    rack=(
                        producto.ubicacion.rack
                        if producto.ubicacion
                        else ''
                    ),

                    espacio=(
                        producto.ubicacion.espacio
                        if producto.ubicacion
                        else ''
                    ),

                    nivel=(
                        producto.ubicacion.nivel
                        if producto.ubicacion
                        else ''
                    ),

                    cantidad_contada=cantidad_contada,
                    diferencia=diferencia
                )

            # =====================================================
            # 4. CERRAR LA BASE
            # =====================================================

            base.estado = 'CERRADA'
            base.fecha_cierre = timezone.now()
            base.cerrado_por = request.user

            base.save(
                update_fields=[
                    'estado',
                    'fecha_cierre',
                    'cerrado_por'
                ]
            )

            # =====================================================
            # 5. CONSERVAR LOS CONTEOS
            # =====================================================
            #
            # Los ConteoDetalle forman parte de la trazabilidad
            # histórica y NO se eliminan.
            #

            # =====================================================
            # 6. CONSERVAR EL MAESTRO DE PRODUCTOS
            # =====================================================
            #
            # Los productos NO se eliminan.
            #
            # El Maestro de Productos representa los artículos
            # actuales de la empresa.
            #
            # La fotografía de esta base queda almacenada en
            # HistorialProducto.
            #

            # =====================================================
            # 7. AUDITORÍA
            # =====================================================

            LogAuditoria.objects.create(
                usuario=request.user,
                accion='MODIFICAR',
                modelo='BaseInventario',
                objeto_id=str(base.id),
                descripcion=(
                    f'Se cerró la base "{base.nombre}". '
                    f'Se archivaron {cantidad_productos} productos '
                    f'en el historial. '
                    f'El Maestro de Productos y los conteos históricos '
                    f'fueron conservados para mantener la trazabilidad.'
                ),
                ip_direccion=get_client_ip(request)
            )

        messages.success(
            request,
            (
                f'La base "{base.nombre}" fue cerrada correctamente. '
                f'{cantidad_productos} productos fueron archivados '
                f'en el historial. '
                f'El Maestro de Productos se conserva para el siguiente '
                f'inventario.'
            )
        )

    except Exception as e:

        messages.error(
            request,
            f'No fue posible cerrar la base: {str(e)}'
        )

    return redirect('inventario:panel_sesiones')