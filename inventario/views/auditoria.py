from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from ..models import LogAuditoria


@login_required
def historial_auditoria(request):

    query = request.GET.get('q', '').strip()
    accion_filter = request.GET.get('accion', '').strip()

    logs = (
        LogAuditoria.objects
        .select_related('usuario')
        .all()
        .order_by('-fecha_hora')
    )

    if query:
        logs = logs.filter(
            Q(usuario__username__icontains=query)
            | Q(descripcion__icontains=query)
            | Q(modelo__icontains=query)
            | Q(objeto_id__icontains=query)
            | Q(ip_direccion__icontains=query)
        )

    if accion_filter:
        logs = logs.filter(
            accion=accion_filter
        )

    acciones_disponibles = LogAuditoria.ACCIONES

    paginator = Paginator(logs, 25)

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'inventario/historial_auditoria.html',
        {
            'page_obj': page_obj,
            'query': query,
            'accion_filter': accion_filter,
            'acciones_disponibles': acciones_disponibles,
        }
    )
