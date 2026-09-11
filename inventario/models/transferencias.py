from django.db import models
from django.conf import settings

from .producto import Producto
from .ubicacion import Ubicacion


class TransferenciaInventario(models.Model):
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='transferencias'
    )

    cantidad = models.PositiveIntegerField()

    ubicacion_origen = models.ForeignKey(
        Ubicacion,
        on_delete=models.PROTECT,
        related_name='transferencias_origen'
    )

    ubicacion_destino = models.ForeignKey(
        Ubicacion,
        on_delete=models.PROTECT,
        related_name='transferencias_destino'
    )

    motivo = models.CharField(
        max_length=255,
        blank=True,
        default=''
    )

    observacion = models.TextField(
        blank=True,
        default=''
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='transferencias_inventario'
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return (
            f'Transferencia - '
            f'{self.producto.codigo_barras} '
            f'({self.cantidad})'
        )