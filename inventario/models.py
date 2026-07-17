from django.db import models
from django.conf import settings
from django.db.models import Sum
from import_export import resources

# =====================================================================
# 1. MODELO PRODUCTO
# =====================================================================
class Producto(models.Model):
    codigo_barras = models.CharField(max_length=100, unique=True, help_text="Código de barras único")
    descripcion = models.CharField(max_length=255, help_text="Nombre o descripción del producto")
    stock_teorico = models.PositiveIntegerField(default=0, help_text="Cantidad esperada en sistema")
    
    # ZONIFICACIÓN
    rack = models.CharField(max_length=20, blank=True, null=True, help_text="Ej: Rack 01")
    espacio = models.CharField(max_length=20, blank=True, null=True, help_text="Ej: A1")
    nivel = models.CharField(max_length=20, blank=True, null=True, help_text="Ej: 01, 02")

    def __str__(self):
        # Incluimos la ubicación en la representación del objeto
        ubicacion = f"{self.rack}-{self.espacio}-{self.nivel}" if (self.rack or self.espacio or self.nivel) else "Sin ubicación"
        return f"{self.codigo_barras} | {self.descripcion} | {ubicacion}"

    # MÉTODO ADAPTADO: Calcula la diferencia contra una sesión específica
    def get_variacion(self, sesion_id):
        total_contado = self.conteos.filter(sesion_id=sesion_id).aggregate(
            Sum('cantidad')
        )['cantidad__sum'] or 0

        return total_contado - self.stock_teorico


# =====================================================================
# 2. MODELOS DE CONTROL DE SESIONES Y CONTEO
# =====================================================================
class SesionInventario(models.Model):
    ESTADOS = (
        ('ABIERTA', 'Abierta / En Conteo'),
        ('CERRADA', 'Cerrada / Finalizada'),
    )
    nombre = models.CharField(max_length=150, help_text="Ej: Inventario General Julio 2026")
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=10, choices=ESTADOS, default='ABIERTA')
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.nombre} ({self.get_estado_display()})"


class ConteoDetalle(models.Model):
    sesion = models.ForeignKey(SesionInventario, on_delete=models.CASCADE, related_name='conteos')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='conteos')
    cantidad = models.PositiveIntegerField(default=1)
    fecha_conteo = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        indexes = [
            models.Index(fields=['sesion', 'producto']),
        ]

    def __str__(self):
        return f"{self.producto.descripcion} - Cantidad: {self.cantidad}"


class Novedad(models.Model):
    MOTIVOS = (
        ('NO_EXISTE', 'Artículo NO registrado / No existe'),
        ('ILEGIBLE', 'Código ilegible'),
        ('DUPLICADO', 'Artículo duplicado'),
        ('SIN_ETIQUETA', 'Producto sin etiqueta'),
    )
    sesion = models.ForeignKey(SesionInventario, on_delete=models.CASCADE, related_name='novedades')
    codigo_barras_detectado = models.CharField(max_length=100, blank=True, null=True)
    descripcion_manual = models.CharField(max_length=255, blank=True, null=True, default="No especificado")
    cantidad = models.PositiveIntegerField(default=1)
    motivo = models.CharField(max_length=20, choices=MOTIVOS, default='NO_EXISTE')
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    def __str__(self):
        return f"Novedad: {self.get_motivo_display()} - Cód: {self.codigo_barras_detectado}"


# =====================================================================
# 3. MODELO DE AUDITORÍA (Trazabilidad automática)
# =====================================================================
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
    accion = models.CharField(max_length=20, choices=ACCIONES, db_index=True, verbose_name="Acción")
    modelo = models.CharField(max_length=50, verbose_name="Modelo / Tabla", blank=True, null=True)
    objeto_id = models.CharField(max_length=50, verbose_name="ID Objeto", blank=True, null=True)
    descripcion = models.TextField(verbose_name="Descripción")
    fecha_hora = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Fecha y Hora")
    ip_direccion = models.GenericIPAddressField(null=True, blank=True, verbose_name="Dirección IP")

    class Meta:
        ordering = ['-fecha_hora']
        verbose_name = "Log de Auditoría"
        verbose_name_plural = "Logs de Auditoría"

    def __str__(self):
        user_str = self.usuario.username if self.usuario else "Sistema"
        return f"{user_str} - {self.get_accion_display()} - {self.fecha_hora.strftime('%d/%m/%Y %I:%M %p')}"


# =====================================================================
# 4. CONFIGURACIÓN DE IMPORTACIÓN / EXPORTACIÓN
# =====================================================================
class ProductoResource(resources.ModelResource):
    class Meta:
        model = Producto
        fields = ('codigo_barras', 'descripcion', 'stock_teorico', 'rack', 'espacio', 'nivel')
        import_id_fields = ('codigo_barras',)