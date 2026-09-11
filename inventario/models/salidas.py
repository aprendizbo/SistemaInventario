from django.db import models
from django.conf import settings

from .producto import Producto
from .ubicacion import Ubicacion


class SalidaInventario(models.Model):
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='salidas'
    )

    cantidad = models.PositiveIntegerField()

    ubicacion = models.ForeignKey(
        Ubicacion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='salidas'
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
        related_name='salidas_inventario'
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return (
            f'Salida - {self.producto.codigo_barras} '
            f'(-{self.cantidad})'
        )