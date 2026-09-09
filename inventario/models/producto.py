from django.db import models
from django.db.models import Sum
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget

from .ubicacion import Ubicacion


class Producto(models.Model):
    codigo_barras = models.CharField(
        max_length=100,
        unique=True,
        help_text="Código de barras único"
    )

    descripcion = models.CharField(
        max_length=255,
        help_text="Nombre o descripción del producto"
    )

    stock_teorico = models.PositiveIntegerField(
        default=0,
        help_text="Cantidad esperada en sistema"
    )

    ubicacion = models.ForeignKey(
        Ubicacion,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='productos',
        help_text="Ubicación física del producto"
    )

    def __str__(self):
        ubicacion_str = (
            str(self.ubicacion)
            if self.ubicacion
            else "Sin ubicación"
        )

        return (
            f"{self.codigo_barras} | "
            f"{self.descripcion} | "
            f"{ubicacion_str}"
        )

    def get_variacion(self, sesion_id):
        total_contado = (
            self.conteos
            .filter(sesion_id=sesion_id)
            .aggregate(
                Sum('cantidad')
            )['cantidad__sum']
            or 0
        )

        return total_contado - self.stock_teorico


class ProductoResource(resources.ModelResource):

    ubicacion = fields.Field(
        column_name='ubicacion',
        attribute='ubicacion',
        widget=ForeignKeyWidget(
            Ubicacion,
            field='codigo_barras'
        )
    )

    class Meta:
        model = Producto
        fields = (
            'codigo_barras',
            'descripcion',
            'stock_teorico',
            'ubicacion'
        )
        import_id_fields = ('codigo_barras',)