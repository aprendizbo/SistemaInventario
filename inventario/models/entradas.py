from django.db import models
from django.conf import settings

from .producto import Producto
from .ubicacion import Ubicacion


class EntradaInventario(models.Model):
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='entradas'
    )

    cantidad = models.PositiveIntegerField()

    ubicacion = models.ForeignKey(
        Ubicacion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='entradas'
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
        related_name='entradas_inventario'
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return (
            f'Entrada - {self.producto.codigo_barras} '
            f'(+{self.cantidad})'
        )