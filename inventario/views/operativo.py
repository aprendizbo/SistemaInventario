from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum, Exists, OuterRef, Value
from django.db.models.functions import Coalesce
from django.shortcuts import render

from inventario.models import Producto, StockUbicacion, Ubicacion


@login_required
def inventario_operativo(request):
    query = request.GET.get('q', '').strip()

    # Consulta base de productos
    productos = (
        Producto.objects
        .prefetch_related(
            'stocks_por_ubicacion__ubicacion'
        )
        .annotate(
            stock_distribuido=Coalesce(
                Sum('stocks_por_ubicacion__cantidad'),
                Value(0)
            ),
            tiene_ubicacion=Exists(
                StockUbicacion.objects.filter(
                    producto=OuterRef('pk'),
                    cantidad__gt=0
                )
            )
        )
        .all()
        .order_by('descripcion')
    )

    # Búsqueda
    if query:
        productos = productos.filter(
            Q(codigo_barras__icontains=query) |
            Q(descripcion__icontains=query)
        )

    # Ubicaciones activas
    ubicaciones = (
        Ubicacion.objects
        .filter(activa=True)
        .order_by('rack', 'espacio', 'nivel')
    )

    # Indicadores
    total_productos = productos.count()

    total_unidades = (
        productos.aggregate(
            total=Sum('stock_teorico')
        )['total'] or 0
    )

    productos_sin_ubicacion = 0
    productos_con_diferencia = 0
    productos_con_inconsistencia = 0

    for producto in productos:
        stock_teorico = producto.stock_teorico or 0
        stock_distribuido = producto.stock_distribuido or 0

        # Cálculos de diferencia para usar en la plantilla
        producto.diferencia_distribucion = stock_teorico - stock_distribuido
        producto.diferencia_absoluta = abs(producto.diferencia_distribucion)

        # 1. No tiene ninguna cantidad distribuida
        if stock_teorico > 0 and stock_distribuido == 0:
            productos_sin_ubicacion += 1

        # 2. Diferencia: Faltan unidades físicamente (distribuido < teórico)
        if stock_distribuido < stock_teorico:
            productos_con_diferencia += 1
            
        # 3. Inconsistencia: Hay más unidades distribuidas que el teórico (distribuido > teórico)
        elif stock_distribuido > stock_teorico:
            productos_con_inconsistencia += 1

    context = {
        'productos': productos,
        'ubicaciones': ubicaciones,
        'query': query,
        'total_productos': total_productos,
        'total_unidades': total_unidades,
        'productos_sin_ubicacion': productos_sin_ubicacion,
        'productos_con_diferencia': productos_con_diferencia,
        'productos_con_inconsistencia': productos_con_inconsistencia,
        'total_ubicaciones': ubicaciones.count(),
    }

    return render(
        request,
        'inventario/inventario_operativo.html',
        context
    )