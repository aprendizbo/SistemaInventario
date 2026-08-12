from .models import BaseInventario


def get_client_ip(request):
    """
    Obtiene la dirección IP real del cliente.
    """

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]

    return request.META.get('REMOTE_ADDR')


def get_base_activa():
    """
    Obtiene la base de inventario actualmente activa.
    """

    return BaseInventario.objects.filter(
        estado='ACTIVA'
    ).order_by('-id').first()