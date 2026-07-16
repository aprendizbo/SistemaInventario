from django.contrib import admin
from .models import RegistroAuditoria

@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    # Usamos solo 'id' para ir a la fija y que el servidor encienda sin errores
    list_display = ('id',)