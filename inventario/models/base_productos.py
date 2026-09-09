from django.db import models

from .bases import BaseInventario
from .producto import Producto


class BaseProducto(models.Model):
    """
    Fotografía de un producto al momento de cargar
    una Base de Inventario.

    Este registro NO cambia aunque posteriormente
    cambie el stock del maestro de productos.
    """

    base = models.ForeignKey(
        BaseInventario,
        on_delete=models.CASCADE,
        related_name='productos_base'
    )

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='bases_historicas'
    )

    codigo_barras = models.CharField(
        max_length=100
    )

    descripcion = models.CharField(
        max_length=255
    )

    stock_teorico = models.PositiveIntegerField(
        default=0
    )

    rack = models.CharField(
        max_length=50,
        blank=True,
        default=''
    )

    espacio = models.CharField(
        max_length=100,
        blank=True,
        default=''
    )

    nivel = models.CharField(
        max_length=50,
        blank=True,
        default=''
    )

    fecha_carga = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['base', 'producto'],
                name='unique_producto_base'
            ),
        ]

        indexes = [
            models.Index(
                fields=['base', 'codigo_barras']
            ),
            models.Index(
                fields=['base', 'descripcion']
            ),
        ]

    def __str__(self):
        return f'{self.codigo_barras} | {self.descripcion}'