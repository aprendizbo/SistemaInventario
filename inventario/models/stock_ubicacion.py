from django.db import models

from .producto import Producto
from .ubicacion import Ubicacion


class StockUbicacion(models.Model):
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='stocks_por_ubicacion'
    )

    ubicacion = models.ForeignKey(
        Ubicacion,
        on_delete=models.PROTECT,
        related_name='stocks'
    )

    cantidad = models.PositiveIntegerField(
        default=0
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['producto', 'ubicacion'],
                name='unique_stock_producto_ubicacion'
            )
        ]

        ordering = [
            'producto',
            'ubicacion',
        ]

    def __str__(self):
        return (
            f'{self.producto.codigo_barras} - '
            f'{self.ubicacion} - '
            f'{self.cantidad} unidades'
        )