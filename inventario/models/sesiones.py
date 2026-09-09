from django.db import models
from django.conf import settings

from .producto import Producto


class SesionInventario(models.Model):

    ESTADOS = (
        ('ABIERTA', 'Abierta / En Conteo'),
        ('CERRADA', 'Cerrada / Finalizada'),
    )

    nombre = models.CharField(
        max_length=150,
        help_text="Ej: Inventario General Julio 2026"
    )

    fecha_inicio = models.DateTimeField(
        auto_now_add=True
    )

    fecha_fin = models.DateTimeField(
        null=True,
        blank=True
    )

    estado = models.CharField(
        max_length=10,
        choices=ESTADOS,
        default='ABIERTA'
    )

    base = models.ForeignKey(
        'BaseInventario',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='sesiones'
    )

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )

    def __str__(self):
        return f"{self.nombre} ({self.get_estado_display()})"


class ConteoDetalle(models.Model):

    sesion = models.ForeignKey(
        SesionInventario,
        on_delete=models.CASCADE,
        related_name='conteos'
    )

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='conteos'
    )

    cantidad = models.PositiveIntegerField(
        default=1
    )

    fecha_conteo = models.DateTimeField(
        auto_now_add=True
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['sesion', 'producto'],
                name='unique_conteo_sesion_producto'
            ),
        ]
        indexes = [
            models.Index(
                fields=['sesion', 'producto']
            ),
        ]

    def __str__(self):
        return (
            f"{self.producto.descripcion} "
            f"- Cantidad: {self.cantidad}"
        )