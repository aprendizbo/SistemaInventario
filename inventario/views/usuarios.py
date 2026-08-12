from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from ..models import LogAuditoria
from .bases import get_client_ip


# ==========================================
# MÓDULO PERSONALIZADO DE USUARIOS Y ACCESOS
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
            usuario=request.user,
            accion='CREAR',
            modelo='User',
            objeto_id=str(nuevo_usuario.id),
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
                usuario=request.user,
                accion='MODIFICAR',
                modelo='User',
                objeto_id=str(usuario_afectado.id),
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
        usuario=request.user,
        accion='MODIFICAR',
        modelo='User',
        objeto_id=str(usuario_afectado.id),
        descripcion=f"Cambió el estado del usuario '{usuario_afectado.username}' a {estado_str}", 
        ip_direccion=get_client_ip(request)
    )
    
    return JsonResponse({
        'status': 'ok',
        'is_active': usuario_afectado.is_active,
        'message': f"El usuario '{usuario_afectado.username}' ahora está {estado_str}."
    })


# ==========================================
# MÓDULO DE HISTORIAL DE AUDITORÍA
# ==========================================

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