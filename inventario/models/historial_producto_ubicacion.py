from django.db import models

from .bases import BaseInventario
from .producto import Producto
from .ubicacion import Ubicacion


class HistorialProductoUbicacion(models.Model):
    """
    Fotografía histórica de la cantidad de un producto
    en una ubicación al momento de cerrar una Base de Inventario.

    Este registro es permanente y permite conservar la
    distribución física del inventario de cada base cerrada.
    """

    base = models.ForeignKey(
        BaseInventario,
        on_delete=models.PROTECT,
        related_name='historial_ubicaciones'
    )

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='historial_ubicaciones'
    )

    ubicacion = models.ForeignKey(
        Ubicacion,
        on_delete=models.PROTECT,
        related_name='historial_productos_ubicaciones'
    )

    cantidad = models.PositiveIntegerField(
        default=0
    )

    fecha_registro = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['base', 'producto', 'ubicacion'],
                name='unique_historial_producto_ubicacion'
            )
        ]

        indexes = [
            models.Index(
                fields=['base', 'producto']
            ),
            models.Index(
                fields=['base', 'ubicacion']
            ),
        ]

        ordering = [
            'producto',
            'ubicacion',
        ]

    def __str__(self):
        return (
            f'{self.base.nombre} | '
            f'{self.producto.codigo_barras} | '
            f'{self.ubicacion} | '
            f'{self.cantidad} unidades'
        )