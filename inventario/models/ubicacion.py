from django.db import models


class Ubicacion(models.Model):
    codigo_barras = models.CharField(
        max_length=100,
        unique=True,
        help_text="Código de barras de la ubicación"
    )

    rack = models.CharField(max_length=50)
    espacio = models.CharField(max_length=100)
    nivel = models.CharField(max_length=50)

    activa = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.rack} / {self.espacio} / {self.nivel}"