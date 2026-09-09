from django.db import models
from django.conf import settings


class BaseInventario(models.Model):

    ESTADOS = (
        ('ACTIVA', 'Activa'),
        ('CERRADA', 'Cerrada'),
    )

    nombre = models.CharField(
        max_length=150,
        default='Base de Inventario'
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    fecha_cierre = models.DateTimeField(
        null=True,
        blank=True
    )

    estado = models.CharField(
        max_length=10,
        choices=ESTADOS,
        default='ACTIVA'
    )

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='bases_inventario_creadas'
    )

    cerrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='bases_inventario_cerradas'
    )

    # ==========================================================
    # CONCILIACIÓN Y AJUSTE FINAL
    # ==========================================================

    conciliacion_aplicada = models.BooleanField(
        default=False,
        help_text=(
            'Indica si la conciliación final de esta base '
            'ya fue aplicada al Maestro de Productos.'
        )
    )

    fecha_conciliacion = models.DateTimeField(
        null=True,
        blank=True
    )

    conciliado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='bases_inventario_conciliadas'
    )

    def __str__(self):
        return f"{self.nombre} - {self.get_estado_display()}"