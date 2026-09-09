from django.db import models
from django.conf import settings


class LogAuditoria(models.Model):

    ACCIONES = [
        ('CREAR', 'Crear'),
        ('MODIFICAR', 'Modificar'),
        ('ELIMINAR', 'Eliminar'),
        ('IMPORTAR', 'Importar'),
        ('EXPORTAR', 'Exportar'),
        ('CONCILIAR', 'Conciliar'),
        ('AJUSTE', 'Aplicar Ajuste'),
        ('LOGIN', 'Inicio de Sesión'),
        ('LOGOUT', 'Cierre de Sesión'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Usuario"
    )

    accion = models.CharField(
        max_length=20,
        choices=ACCIONES,
        db_index=True,
        verbose_name="Acción"
    )

    modelo = models.CharField(
        max_length=50,
        verbose_name="Modelo / Tabla",
        blank=True,
        null=True
    )

    objeto_id = models.CharField(
        max_length=50,
        verbose_name="ID Objeto",
        blank=True,
        null=True
    )

    descripcion = models.TextField(
        verbose_name="Descripción"
    )

    fecha_hora = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Fecha y Hora"
    )

    ip_direccion = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Dirección IP"
    )

    class Meta:
        ordering = ['-fecha_hora']
        verbose_name = "Log de Auditoría"
        verbose_name_plural = "Logs de Auditoría"

    def __str__(self):
        user_str = (
            self.usuario.username
            if self.usuario
            else "Sistema"
        )

        return (
            f"{user_str} - "
            f"{self.get_accion_display()} - "
            f"{self.fecha_hora.strftime('%d/%m/%Y %I:%M %p')}"
        )