# inventario/signals.py
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from .models import LogAuditoria

def obtener_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')

@receiver(user_logged_in)
def log_inicio_sesion(sender, request, user, **kwargs):
    LogAuditoria.objects.create(
        usuario=user,
        accion='LOGIN',
        descripcion=f"El usuario '{user.username}' inició sesión en el sistema.",
        ip_direccion=obtener_ip(request)
    )

@receiver(user_logged_out)
def log_cierre_sesion(sender, request, user, **kwargs):
    if user:
        LogAuditoria.objects.create(
            usuario=user,
            accion='LOGOUT',
            descripcion=f"El usuario '{user.username}' cerró su sesión de trabajo.",
            ip_direccion=obtener_ip(request)
        )