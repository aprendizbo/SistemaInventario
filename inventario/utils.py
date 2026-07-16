# inventario/utils.py
from .models import LogAuditoria

def registrar_auditoria(request, accion, descripcion, modelo=None, objeto_id=None):
    """
    Registra de manera simplificada un evento en el Log de Auditoría de la base de datos.
    """
    # Detectar IP real (por si pasa por Nginx/Gunicorn/Proxies)
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')

    usuario = request.user if request.user and request.user.is_authenticated else None

    LogAuditoria.objects.create(
        usuario=usuario,
        accion=accion,
        modelo=modelo,
        objeto_id=str(objeto_id) if objeto_id else None,
        descripcion=descripcion,
        ip_direccion=ip
    )