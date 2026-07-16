# inventario/resources.py
from import_export import resources
from .models import Producto

class ProductoResource(resources.ModelResource):
    class Meta:
        model = Producto
        # Aquí pon los campos exactos de tu modelo Producto
        fields = ('codigo', 'descripcion', 'stock') 
        import_id_fields = ('codigo',) # Esto es clave para que si el producto existe, se actualice en vez de duplicarse