from django.db import models

from .bases import BaseInventario
from .producto import Producto
from .ubicacion import Ubicacion


class BaseProductoUbicacion(models.Model):
    """
    Fotografía de la distribución de un producto por ubicación
    al momento de crear una Base de Inventario.

    Este registro es histórico y no cambia aunque posteriormente
    cambie el stock del Maestro.
    """

    base = models.ForeignKey(
        BaseInventario,
        on_delete=models.CASCADE,
        related_name='ubicaciones_productos_base'
    )

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='ubicaciones_bases_historicas'
    )

    ubicacion = models.ForeignKey(
        Ubicacion,
        on_delete=models.PROTECT,
        related_name='ubicaciones_bases_historicas'
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
                name='unique_base_producto_ubicacion'
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