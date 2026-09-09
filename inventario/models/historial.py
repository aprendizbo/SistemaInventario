from django.db import models

from .bases import BaseInventario


class HistorialProducto(models.Model):

    base = models.ForeignKey(
        BaseInventario,
        on_delete=models.PROTECT,
        related_name='productos'
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

    cantidad_contada = models.PositiveIntegerField(
        default=0
    )

    diferencia = models.IntegerField(
        default=0
    )

    fecha_registro = models.DateTimeField(
        auto_now_add=True
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        indexes = [
            models.Index(
                fields=['base', 'codigo_barras']
            ),
            models.Index(
                fields=['base', 'descripcion']
            ),
        ]

    def __str__(self):
        return f"{self.codigo_barras} | {self.descripcion}"