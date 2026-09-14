from django.db import models
from django.conf import settings

from .producto import Producto
from .ubicacion import Ubicacion


class MovimientoInventario(models.Model):
    TIPOS = (
        ('ENTRADA', 'Entrada'),
        ('SALIDA', 'Salida'),
        ('TRANSFERENCIA', 'Transferencia'),
    )

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='movimientos_kardex'
    )

    tipo = models.CharField(
        max_length=20,  # <-- Correctamente ajustado a 20
        choices=TIPOS
    )

    cantidad = models.PositiveIntegerField()

    stock_anterior = models.PositiveIntegerField(
        default=0
    )

    stock_posterior = models.PositiveIntegerField(
        default=0
    )

    ubicacion = models.ForeignKey(
        Ubicacion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='movimientos_kardex'
    )

    ubicacion_origen = models.ForeignKey(
        Ubicacion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='movimientos_kardex_origen'
    )

    ubicacion_destino = models.ForeignKey(
        Ubicacion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='movimientos_kardex_destino'
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
        related_name='movimientos_kardex'
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        if self.tipo == 'ENTRADA':
            signo = '+'
        elif self.tipo == 'SALIDA':
            signo = '-'
        else:
            signo = '⇄ ' # Para las transferencias

        return (
            f'{self.tipo} - '
            f'{self.producto.codigo_barras} '
            f'({signo}{self.cantidad})'
        )