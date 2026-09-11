from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from ..models import MovimientoInventario, Producto


@login_required
def kardex(request):
    movimientos = MovimientoInventario.objects.select_related(
        'producto',
        'ubicacion',
        'usuario',
    ).order_by('-fecha')

    productos = Producto.objects.order_by('descripcion')

    producto_id = request.GET.get('producto', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    busqueda = request.GET.get('buscar', '').strip()

    if producto_id:
        movimientos = movimientos.filter(
            producto_id=producto_id
        )

    if tipo in ['ENTRADA', 'SALIDA']:
        movimientos = movimientos.filter(
            tipo=tipo
        )

    if busqueda:
        movimientos = movimientos.filter(
            producto__codigo_barras__icontains=busqueda
        ) | movimientos.filter(
            producto__descripcion__icontains=busqueda
        )

    return render(
        request,
        'inventario/kardex.html',
        {
            'movimientos': movimientos,
            'productos': productos,
            'producto_id': producto_id,
            'tipo': tipo,
            'busqueda': busqueda,
        }
    )