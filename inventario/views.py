import json
import csv
import pandas as pd
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import F, Sum, Q
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from tablib import Dataset

# Modelos
from .models import (
    SesionInventario, 
    Producto, 
    ConteoDetalle, 
    Novedad, 
    LogAuditoria,
    Ubicacion
)
from .forms import ProductoForm
from .admin import ProductoResource 

# ==========================================
# FUNCIÓN AUXILIAR PARA AUDITORÍA
# ==========================================
def get_client_ip(request):
    """Obtiene la dirección IP real del cliente para guardarla en el Log."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


# ==========================================
# 1. MÓDULO DE GESTIÓN DE SESIONES
# ==========================================

@login_required
def panel_sesiones(request):
    sesiones = SesionInventario.objects.all().order_by('-id')
    return render(request, 'inventario/panel_sesiones.html', {'sesiones': sesiones})


@login_required
@require_POST
def crear_sesion(request):
    nombre = request.POST.get('nombre_sesion')
    if not nombre:
        fecha_str = timezone.now().strftime("%Y-%m-%d %H:%M")
        nombre = f"Inventario General - {fecha_str}"
    
    sesion = SesionInventario.objects.create(
        nombre=nombre,
        estado='ABIERTA',
        creado_por=request.user
    )
    
    LogAuditoria.objects.create(
        usuario=request.user, accion='CREAR', modelo='SesionInventario', objeto_id=str(sesion.id),
        descripcion=f"Apertura de nueva sesión de inventario: {sesion.nombre}", ip_direccion=get_client_ip(request)
    )
    return redirect('inventario:panel_sesiones')


@login_required
def cerrar_sesion(request, sesion_id):
    sesion = get_object_or_404(SesionInventario, id=sesion_id)
    sesion.estado = 'CERRADA'
    sesion.save()
    
    LogAuditoria.objects.create(
        usuario=request.user, accion='MODIFICAR', modelo='SesionInventario', objeto_id=str(sesion.id),
        descripcion=f"Cierre de sesión de inventario: {sesion.nombre}", ip_direccion=get_client_ip(request)
    )
    return redirect('inventario:panel_sesiones')


@login_required
def eliminar_sesion(request, sesion_id):
    if not request.user.is_superuser:
        messages.error(request, "No tiene permisos para realizar esta acción.")
        return redirect('inventario:panel_sesiones')

    sesion = get_object_or_404(SesionInventario, id=sesion_id)
    nombre_sesion = sesion.nombre

    # Auditoría (Incluyendo la captura de IP para mantener tu estándar)
    LogAuditoria.objects.create(
        usuario=request.user,
        accion='ELIMINAR',
        modelo='SesionInventario',
        objeto_id=str(sesion.id),
        descripcion=f'Se eliminó la sesión "{nombre_sesion}"',
        ip_direccion=get_client_ip(request)
    )

    sesion.delete()

    messages.success(request, f'Sesión "{nombre_sesion}" eliminada correctamente.')
    return redirect('inventario:panel_sesiones')


# ==========================================
# 2. MÓDULO DE ESCANEO DE PRODUCTOS
# ==========================================

@login_required
def pantalla_escaner(request, sesion_id):
    sesion = get_object_or_404(SesionInventario, id=sesion_id, estado='ABIERTA')
    recientes = ConteoDetalle.objects.filter(sesion=sesion).select_related('producto', 'producto__ubicacion').order_by('-id')[:5]
    
    return render(request, 'inventario/escaner.html', {
        'sesion': sesion,
        'recientes': recientes
    })


@login_required
@require_POST
def procesar_escaneo(request):
    try:
        data = json.loads(request.body)
        codigo = data.get('codigo_barras')
        sesion_id = data.get('sesion_id')
        cantidad_ingresada = int(data.get('cantidad', 1))
        
    except (json.JSONDecodeError, AttributeError, ValueError):
        return JsonResponse({'status': 'error', 'message': 'Datos inválidos.'}, status=400)

    if not codigo or not sesion_id:
        return JsonResponse({'status': 'error', 'message': 'Faltan datos (código o sesión).'}, status=400)

    sesion = get_object_or_404(SesionInventario, id=sesion_id, estado='ABIERTA')

    try:
        try:
            # Traemos la relación ubicación para optimizar las queries
            producto = Producto.objects.select_related('ubicacion').get(codigo_barras=codigo)
        except Producto.MultipleObjectsReturned:
            return JsonResponse({'status': 'error', 'message': f'Error: Códigos duplicados para [{codigo}]'}, status=400)
        except Exception as e:
            raise e

        conteo, created = ConteoDetalle.objects.get_or_create(
            sesion=sesion,
            producto=producto,
            usuario=request.user,
            defaults={'cantidad': cantidad_ingresada}
        )
        
        if not created:
            ConteoDetalle.objects.filter(id=conteo.id).update(cantidad=F('cantidad') + cantidad_ingresada)
            conteo.refresh_from_db()

        return JsonResponse({
            'status': 'ok',
            'tipo': 'conteo',
            'message': f'Producto: {producto.descripcion}',
            'producto': producto.descripcion,
            'cantidad': conteo.cantidad,
            'codigo': producto.codigo_barras,
            'stock_teorico': producto.stock_teorico,
            'rack': producto.ubicacion.rack if producto.ubicacion else '',
            'espacio': producto.ubicacion.espacio if producto.ubicacion else '',
            'nivel': producto.ubicacion.nivel if producto.ubicacion else '',
            'diferencia': conteo.cantidad - producto.stock_teorico,
        })

    except Producto.DoesNotExist:
        novedad, created = Novedad.objects.get_or_create(
            sesion=sesion,
            codigo_barras_detectado=codigo,
            motivo='NO_EXISTE',
            usuario=request.user,
            defaults={'cantidad': cantidad_ingresada}
        )
        
        if not created:
            Novedad.objects.filter(id=novedad.id).update(cantidad=F('cantidad') + cantidad_ingresada)
            novedad.refresh_from_db()

        return JsonResponse({
            'status': 'novedad',
            'tipo': 'no_registrado',
            'message': f'Código [{codigo}] no encontrado. Guardado en Novedades.',
            'codigo': codigo,
            'cantidad': novedad.cantidad
        })


# ==========================================
# 3. MAESTRO GENERAL Y CATÁLOGOS
# ==========================================

@login_required
def lista_productos(request):
    query = request.GET.get('q', '')
    
    if query:
        productos_list = Producto.objects.select_related('ubicacion').filter(
            Q(codigo_barras__icontains=query) | 
            Q(descripcion__icontains=query)
        ).order_by('-id')
    else:
        productos_list = Producto.objects.select_related('ubicacion').all().order_by('-id')
        
    paginator = Paginator(productos_list, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'inventario/lista_productos.html', {
        'page_obj': page_obj,
        'query': query
    })


@login_required
def importar_productos(request):
    if request.method == 'POST' and request.FILES.get('archivo_excel'):
        excel_file = request.FILES['archivo_excel']

        try:
            df = pd.read_excel(excel_file)
            df = df.fillna({
                'Código de barras': '',
                'Descripción': 'Sin descripción',
                'Cantidad': 0,
                'Almacén': '',
                'Ubicación de almacenaje': ''
            })

            productos_crear = []
            productos_actualizar = []
            
            codigos_db = set(Producto.objects.values_list('codigo_barras', flat=True))
            
            for index, row in df.iterrows():
                codigo = str(row.get('Código de barras', '')).strip()
                if codigo.endswith('.0'):
                    codigo = codigo[:-2]
                
                if not codigo or codigo.lower() == 'nan':
                    continue  

                descripcion = str(row.get('Descripción', '')).strip()
                stock = row.get('Cantidad', 0)
                
                rack = str(row.get('Almacén', '')).strip()
                espacio = str(row.get('Ubicación de almacenaje', '')).strip()
                nivel = '' 
                
                rack = rack if rack.lower() != 'nan' else ''
                espacio = espacio if espacio.lower() != 'nan' else ''
                nivel = nivel if nivel.lower() != 'nan' else ''

                try:
                    stock = int(stock)
                except (ValueError, TypeError):
                    stock = 0

                ubicacion = None
                if rack or espacio or nivel:
                    ubicacion, _ = Ubicacion.objects.get_or_create(
                        codigo_barras=f"{rack}-{espacio}-{nivel}",
                        defaults={
                            'rack': rack,
                            'espacio': espacio,
                            'nivel': nivel,
                        }
                    )

                if codigo in codigos_db:
                    try:
                        prod = Producto.objects.get(codigo_barras=codigo)

                        prod.descripcion = descripcion
                        prod.stock_teorico = stock
                        prod.ubicacion = ubicacion

                        productos_actualizar.append(prod)

                    except Producto.DoesNotExist:
                        pass
                    except Producto.MultipleObjectsReturned:
                        pass
                else:
                    productos_crear.append(Producto(
                        codigo_barras=codigo,
                        descripcion=descripcion,
                        stock_teorico=stock,
                        ubicacion=ubicacion
                    ))
                    codigos_db.add(codigo)

            if productos_crear:
                Producto.objects.bulk_create(productos_crear)
            
            if productos_actualizar:
                Producto.objects.bulk_update(
                    productos_actualizar, 
                    ['descripcion', 'stock_teorico', 'ubicacion']
                )

            LogAuditoria.objects.create(
                usuario=request.user, accion='IMPORTAR', modelo='Producto',
                descripcion=f"Importación Excel exitosa. Creados: {len(productos_crear)}, Actualizados: {len(productos_actualizar)}", 
                ip_direccion=get_client_ip(request)
            )
            
            messages.success(request, f"Importación correcta: {len(productos_crear)} creados y {len(productos_actualizar)} actualizados.")

        except Exception as e:
            messages.error(request, f"Error al procesar el archivo Excel: {str(e)}.")
            
        return redirect('inventario:lista_productos')
        
    return render(request, 'inventario/importar_productos.html')


@login_required
def exportar_excel(request):
    producto_resource = ProductoResource()
    dataset = producto_resource.export()
    
    LogAuditoria.objects.create(
        usuario=request.user, accion='EXPORTAR', modelo='Producto',
        descripcion="Descarga del maestro general de productos en Excel", 
        ip_direccion=get_client_ip(request)
    )
    
    response = HttpResponse(
        dataset.xlsx, 
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="maestro_productos.xlsx"'
    
    return response


# ==========================================
# 4. MÓDULOS DE ADMINISTRACIÓN PROPIOS
# ==========================================

@login_required
def crear_producto(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            producto = form.save()
            
            LogAuditoria.objects.create(
                usuario=request.user, accion='CREAR', modelo='Producto', objeto_id=str(producto.id),
                descripcion=f"Creación manual de producto: {producto.codigo_barras}", 
                ip_direccion=get_client_ip(request)
            )
            
            return redirect('inventario:lista_productos')
    else:
        form = ProductoForm()
    
    return render(request, 'inventario/crear_producto.html', {'form': form})


# ==========================================
# 5. PANEL DE NOVEDADES
# ==========================================

@login_required
def lista_novedades(request):
    novedades = Novedad.objects.select_related('sesion', 'usuario').all().order_by('-id')
    return render(request, 'inventario/novedades.html', {'novedades': novedades})


# ==========================================
# 6. REPORTES Y AUDITORÍA
# ==========================================

@login_required
def exportar_conteo_csv(request, sesion_id):
    sesion = get_object_or_404(SesionInventario, id=sesion_id)
    
    LogAuditoria.objects.create(
        usuario=request.user, accion='EXPORTAR', modelo='ConteoDetalle', objeto_id=str(sesion.id),
        descripcion=f"Exportación CSV sesión: {sesion.nombre}", 
        ip_direccion=get_client_ip(request)
    )
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="historial_sesion_{sesion_id}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID Sesion', 'Nombre Sesion', 'Codigo de Barras', 'Descripcion', 'Stock Teorico', 'Cantidad', 'Operario'])
    
    conteos = ConteoDetalle.objects.filter(sesion=sesion).select_related('producto', 'usuario')
    for item in conteos:
        writer.writerow([
            sesion.id,
            sesion.nombre,
            item.producto.codigo_barras,
            item.producto.descripcion,
            item.producto.stock_teorico, 
            item.cantidad,
            item.usuario.username
        ])
        
    return response


# ==========================================
# 7. MÓDULO DE CONCILIACIÓN
# ==========================================

@login_required
def conciliacion_sesion(request, sesion_id):
    sesion = get_object_or_404(SesionInventario, id=sesion_id)
    productos = Producto.objects.select_related('ubicacion').all()
    resultados = []

    for p in productos:
        cantidad_escaneada = p.conteos.filter(sesion=sesion).aggregate(Sum('cantidad'))['cantidad__sum'] or 0
        diferencia = cantidad_escaneada - p.stock_teorico

        if cantidad_escaneada > 0 or p.stock_teorico > 0:
            resultados.append({
                'producto': p,
                'stock_teorico': p.stock_teorico,
                'cantidad_escaneada': cantidad_escaneada,
                'diferencia': diferencia,
            })

    return render(request, 'inventario/conciliacion.html', {'sesion': sesion, 'resultados': resultados})


@login_required
@require_POST
def aplicar_ajuste_inventario(request, sesion_id):
    sesion = get_object_or_404(SesionInventario, id=sesion_id)

    if sesion.estado == 'CERRADA':
        messages.error(request, "Esta sesión ya fue cerrada.")
        return redirect('inventario:conciliacion', sesion_id=sesion.id)

    productos = Producto.objects.all()
    for p in productos:
        cantidad_escaneada = p.conteos.filter(sesion=sesion).aggregate(Sum('cantidad'))['cantidad__sum'] or 0
        if cantidad_escaneada > 0 or p.stock_teorico > 0:
            p.stock_teorico = cantidad_escaneada
            p.save()

    sesion.estado = 'CERRADA'
    sesion.fecha_fin = timezone.now()
    sesion.save()
    
    LogAuditoria.objects.create(
        usuario=request.user, accion='AJUSTE', modelo='Producto', objeto_id=str(sesion.id),
        descripcion=f"Ajuste general de inventario basado en sesión: {sesion.nombre}", 
        ip_direccion=get_client_ip(request)
    )

    messages.success(request, f"Inventario '{sesion.nombre}' aplicado exitosamente.")
    return redirect('inventario:panel_sesiones')


# ==========================================
# 8. RESOLUCIÓN DE NOVEDADES
# ==========================================

@login_required
def asociar_novedad(request, novedad_id):
    novedad = get_object_or_404(Novedad, id=novedad_id)
    
    if request.method == 'POST':
        producto_id = request.POST.get('producto_id')
        if producto_id:
            producto = get_object_or_404(Producto, id=producto_id)
            codigo_viejo = producto.codigo_barras
            producto.codigo_barras = novedad.codigo_barras_detectado
            producto.save()
            
            conteo, created = ConteoDetalle.objects.get_or_create(
                sesion=novedad.sesion,
                producto=producto,
                usuario=novedad.usuario,
                defaults={'cantidad': novedad.cantidad}
            )
            if not created:
                ConteoDetalle.objects.filter(id=conteo.id).update(cantidad=F('cantidad') + novedad.cantidad)
            
            novedad.delete()
            
            LogAuditoria.objects.create(
                usuario=request.user, accion='CONCILIAR', modelo='Producto', objeto_id=str(producto.id),
                descripcion=f"Novedad resuelta. Código '{codigo_viejo}' actualizado a '{producto.codigo_barras}' para el producto '{producto.descripcion}'", 
                ip_direccion=get_client_ip(request)
            )
            
            messages.success(request, f"¡Éxito! Código asignado a '{producto.descripcion}' y conteo consolidado.")
            return redirect('inventario:lista_novedades')
            
    productos = Producto.objects.all().order_by('descripcion')
    return render(request, 'inventario/asociar_novedad.html', {
        'novedad': novedad,
        'productos': productos
    })


@login_required
def crear_desde_novedad(request, novedad_id):
    novedad = get_object_or_404(Novedad, id=novedad_id)
    
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            nuevo_producto = form.save()
            
            conteo, created = ConteoDetalle.objects.get_or_create(
                sesion=novedad.sesion,
                producto=nuevo_producto,
                usuario=novedad.usuario,
                defaults={'cantidad': novedad.cantidad}
            )
            if not created:
                ConteoDetalle.objects.filter(id=conteo.id).update(cantidad=F('cantidad') + novedad.cantidad)
                
            novedad.delete()
            
            LogAuditoria.objects.create(
                usuario=request.user, accion='CREAR', modelo='Producto', objeto_id=str(nuevo_producto.id),
                descripcion=f"Resolución de novedad. Creó producto nuevo: {nuevo_producto.codigo_barras} - {nuevo_producto.descripcion}", 
                ip_direccion=get_client_ip(request)
            )
            
            messages.success(request, f"¡Ficha creada! Producto '{nuevo_producto.descripcion}' registrado con conteo asociado.")
            return redirect('inventario:lista_novedades')
    else:
        form = ProductoForm(initial={
            'codigo_barras': novedad.codigo_barras_detectado,
            'stock_teorico': 0
        })
        
    return render(request, 'inventario/crear_desde_novedad.html', {
        'form': form,
        'novedad': novedad
    })


# ==========================================
# 9. MÓDULO PERSONALIZADO DE USUARIOS Y ACCESOS
# ==========================================

@login_required
def lista_usuarios(request):
    if not request.user.is_staff:
        messages.error(request, "No tiene privilegios de administrador para acceder a este módulo.")
        return redirect('inventario:panel_sesiones')
        
    usuarios = User.objects.all().order_by('-is_staff', 'username')
    return render(request, 'inventario/lista_usuarios.html', {'usuarios': usuarios})


@login_required
def crear_usuario(request):
    if not request.user.is_staff:
        messages.error(request, "No tiene privilegios para realizar esta acción.")
        return redirect('inventario:panel_sesiones')

    if request.method == 'POST':
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        is_admin = request.POST.get('is_staff') == 'on'

        if not username or not password:
            messages.error(request, "El nombre de usuario y la contraseña son obligatorios.")
            return render(request, 'inventario/crear_usuario.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, f"El nombre de usuario '{username}' ya está registrado.")
            return render(request, 'inventario/crear_usuario.html')

        nuevo_usuario = User.objects.create(
            username=username,
            first_name=first_name,
            last_name=last_name,
            is_staff=is_admin,
            is_superuser=is_admin 
        )
        nuevo_usuario.set_password(password) 
        nuevo_usuario.save()

        LogAuditoria.objects.create(
            usuario=request.user, accion='CREAR', modelo='User', objeto_id=str(nuevo_usuario.id),
            descripcion=f"Registro de nuevo usuario de sistema: {nuevo_usuario.username} (Admin: {is_admin})", 
            ip_direccion=get_client_ip(request)
        )

        messages.success(request, f"¡Éxito! El usuario '{username}' ha sido registrado en el sistema.")
        return redirect('inventario:lista_usuarios')

    return render(request, 'inventario/crear_usuario.html')


@login_required
def cambiar_password_usuario(request, user_id):
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado.")
        return redirect('inventario:panel_sesiones')

    usuario_afectado = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        nueva_pass = request.POST.get('password')
        if not nueva_pass:
            messages.error(request, "La contraseña no puede estar vacía.")
        else:
            usuario_afectado.set_password(nueva_pass)
            usuario_afectado.save()
            
            LogAuditoria.objects.create(
                usuario=request.user, accion='MODIFICAR', modelo='User', objeto_id=str(usuario_afectado.id),
                descripcion=f"Restablecimiento de contraseña para el usuario: {usuario_afectado.username}", 
                ip_direccion=get_client_ip(request)
            )
            
            messages.success(request, f"Contraseña restablecida con éxito para '{usuario_afectado.username}'.")
            return redirect('inventario:lista_usuarios')

    return render(request, 'inventario/cambiar_password_usuario.html', {'usuario_afectado': usuario_afectado})


@login_required
@require_POST
def toggle_usuario(request, user_id):
    if not request.user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'No autorizado.'}, status=403)

    usuario_afectado = get_object_or_404(User, id=user_id)

    if usuario_afectado == request.user:
        return JsonResponse({'status': 'error', 'message': 'No puedes desactivar tu propia cuenta.'}, status=400)

    usuario_afectado.is_active = not usuario_afectado.is_active
    usuario_afectado.save()

    estado_str = "Activo" if usuario_afectado.is_active else "Inactivo"
    
    LogAuditoria.objects.create(
        usuario=request.user, accion='MODIFICAR', modelo='User', objeto_id=str(usuario_afectado.id),
        descripcion=f"Cambió el estado del usuario '{usuario_afectado.username}' a {estado_str}", 
        ip_direccion=get_client_ip(request)
    )
    
    return JsonResponse({
        'status': 'ok',
        'is_active': usuario_afectado.is_active,
        'message': f"El usuario '{usuario_afectado.username}' ahora está {estado_str}."
    })


@login_required
def historial_auditoria(request):
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado.")
        return redirect('inventario:panel_sesiones')

    logs = LogAuditoria.objects.select_related(
        'usuario'
    ).order_by('-fecha_hora')

    return render(
        request,
        'inventario/auditoria.html',
        {
            'logs': logs,
            'total_logs': logs.count(),
            'total_crear': logs.filter(accion='CREAR').count(),
            'total_modificar': logs.filter(accion='MODIFICAR').count(),
            'total_exportar': logs.filter(accion='EXPORTAR').count(),
        }
    )