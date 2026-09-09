from django.db import models
from django.conf import settings

from .sesiones import SesionInventario


class Novedad(models.Model):

    MOTIVOS = (
        ('NO_EXISTE', 'Artículo NO registrado / No existe'),
        ('ILEGIBLE', 'Código ilegible'),
        ('DUPLICADO', 'Artículo duplicado'),
        ('SIN_ETIQUETA', 'Producto sin etiqueta'),
    )

    sesion = models.ForeignKey(
        SesionInventario,
        on_delete=models.CASCADE,
        related_name='novedades'
    )

    codigo_barras_detectado = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    descripcion_manual = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default="No especificado"
    )

    cantidad = models.PositiveIntegerField(
        default=1
    )

    motivo = models.CharField(
        max_length=20,
        choices=MOTIVOS,
        default='NO_EXISTE'
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )

    def __str__(self):
        return (
            f"Novedad: {self.get_motivo_display()} "
            f"- Cód: {self.codigo_barras_detectado}"
        )