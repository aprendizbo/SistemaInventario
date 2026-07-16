from django.db import models
from django.conf import settings

class RegistroAuditoria(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    accion = models.CharField(max_length=255) # Ej: "Importó inventario", "Cerró sesión"
    modulo = models.CharField(max_length=50) # Ej: "Catálogo", "Usuarios", "Conteo"
    fecha_hora = models.DateTimeField(auto_now_add=True)
    detalles = models.TextField(blank=True, null=True)

    def __str__(self):
        usuario_str = self.usuario.username if self.usuario else "Sistema/Eliminado"
        return f"{usuario_str} - {self.accion} ({self.fecha_hora.strftime('%d/%m/%Y %H:%M')})"