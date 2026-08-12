from django.db import transaction
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum

from ..models import (
    BaseInventario,
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

    if request.method != 'POST':
        return redirect('inventario:panel_sesiones')

    # Verificar si ya existe una base activa
    base_existente = BaseInventario.objects.filter(estado='ACTIVA').first()

    if base_existente:
        messages.error(
            request,
            f'Ya existe una base activa: "{base_existente.nombre}". '
            f'Debe cerrarla antes de crear una nueva.'
        )
        return redirect('inventario:panel_sesiones')

    nombre = request.POST.get('nombre_base', '').strip()

    if not nombre:
        fecha = timezone.now().strftime('%d/%m/%Y %H:%M')
        nombre = f'Base de Inventario - {fecha}'

    base = BaseInventario.objects.create(
        nombre=nombre,
        estado='ACTIVA',
        creado_por=request.user
    )

    LogAuditoria.objects.create(
        usuario=request.user,
        accion='CREAR',
        modelo='BaseInventario',
        objeto_id=str(base.id),
        descripcion=f'Se creó la base de inventario "{base.nombre}".',
        ip_direccion=get_client_ip(request)
    )

    messages.success(
        request,
        f'Base "{base.nombre}" creada correctamente.'
    )

    return redirect('inventario:panel_sesiones')


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
            # 1. OBTENER PRODUCTOS ACTUALES
            # =====================================================

            productos = Producto.objects.select_related(
                'ubicacion'
            ).all()

            cantidad_productos = productos.count()

            # =====================================================
            # 2. OBTENER SESIONES CERRADAS
            # =====================================================

            sesiones = SesionInventario.objects.filter(
                base=base,
                estado='CERRADA'
            )

            # =====================================================
            # 3. GUARDAR CADA PRODUCTO EN EL HISTORIAL
            # =====================================================

            for producto in productos:

                cantidad_contada = 0

                for sesion in sesiones:

                    total = (
                        producto.conteos
                        .filter(sesion=sesion)
                        .aggregate(
                            total=Sum('cantidad')
                        )['total']
                        or 0
                    )

                    cantidad_contada += total

                diferencia = (
                    cantidad_contada -
                    producto.stock_teorico
                )

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
            # 5. ELIMINAR LOS CONTEOS
            # =====================================================
            #
            # Producto tiene on_delete=PROTECT en ConteoDetalle,
            # por eso primero debemos eliminar los conteos.
            #

            ConteoDetalle.objects.filter(
                producto__in=productos
            ).delete()

            # =====================================================
            # 6. ELIMINAR PRODUCTOS DEL MAESTRO
            # =====================================================

            Producto.objects.filter(
                id__in=productos.values('id')
            ).delete()

            # =====================================================
            # 7. AUDITORÍA
            # =====================================================

            LogAuditoria.objects.create(
                usuario=request.user,
                accion='ELIMINAR',
                modelo='BaseInventario',
                objeto_id=str(base.id),
                descripcion=(
                    f'Se cerró la base "{base.nombre}". '
                    f'Se archivaron {cantidad_productos} productos '
                    f'en el historial y se limpió el maestro actual.'
                ),
                ip_direccion=get_client_ip(request)
            )

        # =========================================================
        # 8. MENSAJE FINAL
        # =========================================================

        messages.success(
            request,
            (
                f'La base "{base.nombre}" fue cerrada correctamente. '
                f'{cantidad_productos} productos fueron archivados '
                f'y retirados del Maestro de Productos.'
            )
        )

    except Exception as e:

        messages.error(
            request,
            f'No fue posible cerrar la base: {str(e)}'
        )

    return redirect('inventario:panel_sesiones')
