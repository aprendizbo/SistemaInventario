from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import (
    Producto,
    Ubicacion,
    SesionInventario,
    ConteoDetalle,
    Novedad
)

# 1. Definimos el recurso para tener control total de los campos exportados
class ProductoResource(resources.ModelResource):
    class Meta:
        model = Producto
        fields = ('codigo_barras', 'descripcion', 'stock_teorico', 'ubicacion')
        export_order = ('codigo_barras', 'descripcion', 'stock_teorico', 'ubicacion')

@admin.register(Producto)
class ProductoAdmin(ImportExportModelAdmin):
    resource_class = ProductoResource

    list_display = (
        'codigo_barras',
        'descripcion',
        'stock_teorico',
        'ubicacion'
    )

    search_fields = (
        'codigo_barras',
        'descripcion',
        'ubicacion__rack',
        'ubicacion__espacio',
        'ubicacion__nivel'
    )

    list_filter = (
        'ubicacion',
    )

@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
    list_display = (
        'codigo_barras',
        'rack',
        'espacio',
        'nivel',
        'activa'
    )

    list_filter = (
        'rack',
        'nivel',
        'activa'
    )

    search_fields = (
        'codigo_barras',
        'rack',
        'espacio',
        'nivel'
    )

    ordering = (
        'rack',
        'espacio',
        'nivel'
    )

@admin.register(SesionInventario)
class SesionInventarioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'estado', 'fecha_inicio', 'fecha_fin', 'creado_por')
    list_filter = ('estado', 'fecha_inicio')
    search_fields = ('nombre',)

@admin.register(ConteoDetalle)
class ConteoDetalleAdmin(admin.ModelAdmin):
    list_display = ('sesion', 'producto', 'cantidad', 'fecha_conteo', 'usuario')
    list_filter = ('sesion', 'fecha_conteo')
    search_fields = ('producto__descripcion', 'producto__codigo_barras', 'usuario__username')

@admin.register(Novedad)
class NovedadAdmin(admin.ModelAdmin):
    list_display = ('sesion', 'motivo', 'codigo_barras_detectado', 'cantidad', 'fecha', 'usuario')
    list_filter = ('motivo', 'sesion')
    search_fields = ('codigo_barras_detectado', 'descripcion_manual')