from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from inventario.forms import UbicacionForm
from inventario.models import Ubicacion

@login_required
def lista_ubicaciones(request):
    ubicaciones = (
        Ubicacion.objects
        .annotate(
            cantidad_productos=Count('productos')
        )
        .order_by(
            '-activa',
            'rack',
            'espacio',
            'nivel',
        )
    )

    return render(
        request,
        'inventario/ubicaciones.html',
        {
            'ubicaciones': ubicaciones,
        }
    )

@login_required
def crear_ubicacion(request):
    if request.method == 'POST':
        form = UbicacionForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                ubicacion = form.save()
            messages.success(
                request,
                'La ubicación se registró correctamente.'
            )
            return redirect('inventario:lista_ubicaciones')
    else:
        form = UbicacionForm()
        
    return render(
        request,
        'inventario/ubicaciones.html',
        {
            'form': form,
            'modo': 'crear',
        }
    )

@login_required
def editar_ubicacion(request, ubicacion_id):
    ubicacion = get_object_or_404(
        Ubicacion,
        id=ubicacion_id
    )
    
    if request.method == 'POST':
        form = UbicacionForm(
            request.POST,
            instance=ubicacion
        )
        if form.is_valid():
            with transaction.atomic():
                form.save()
            messages.success(
                request,
                'La ubicación se actualizó correctamente.'
            )
            return redirect('inventario:lista_ubicaciones')
    else:
        form = UbicacionForm(instance=ubicacion)
        
    return render(
        request,
        'inventario/ubicaciones.html',
        {
            'form': form,
            'ubicacion': ubicacion,
            'modo': 'editar',
        }
    )

@login_required
def toggle_ubicacion(request, ubicacion_id):
    if request.method != 'POST':
        return redirect('inventario:lista_ubicaciones')
        
    ubicacion = get_object_or_404(
        Ubicacion,
        id=ubicacion_id
    )
    
    ubicacion.activa = not ubicacion.activa
    ubicacion.save(
        update_fields=['activa']
    )
    
    if ubicacion.activa:
        messages.success(
            request,
            'La ubicación fue activada correctamente.'
        )
    else:
        messages.warning(
            request,
            'La ubicación fue desactivada correctamente.'
        )
        
    return redirect('inventario:lista_ubicaciones')