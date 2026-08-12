import pandas as pd

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from ..models import (
    Producto,
    Ubicacion,
    LogAuditoria,
)
from ..forms import ProductoForm
from ..admin import ProductoResource

# Importamos las funciones auxiliares desde bases.py
from .bases import get_client_ip, get_base_activa


@login_required
def lista_productos(request):
    query = request.GET.get('q', '')

    if query:
        productos_list = Producto.objects.select_related(
            'ubicacion'
        ).filter(
            Q(codigo_barras__icontains=query) |
            Q(descripcion__icontains=query)
        ).order_by('-id')
    else:
        # Se removió activo=True, ahora trae todos
        productos_list = Producto.objects.select_related(
            'ubicacion'
        ).all().order_by('-id')

    paginator = Paginator(productos_list, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    base_activa = get_base_activa()

    return render(
        request,
        'inventario/lista_productos.html',
        {
            'page_obj': page_obj,
            'query': query,
            'base_activa': base_activa,
        }
    )


@login_required
def importar_productos(request):
    if request.method != 'POST' or not request.FILES.get('archivo_excel'):
        return render(
            request,
            'inventario/importar_productos.html'
        )

    excel_file = request.FILES['archivo_excel']

    try:
        # ============================================================
        # 1. BASE ACTIVA OBLIGATORIA
        # ============================================================

        base_activa = get_base_activa()

        if not base_activa:
            messages.error(
                request,
                'No existe una base de inventario activa. '
                'Debe crear una base antes de importar productos.'
            )
            return redirect('inventario:lista_productos')

        # ============================================================
        # 2. VALIDAR EXTENSIÓN
        # ============================================================

        nombre_archivo = excel_file.name.lower()

        extensiones_permitidas = (
            '.xlsx',
            '.xls',
            '.csv',
            '.ods',
        )

        if not nombre_archivo.endswith(extensiones_permitidas):
            messages.error(
                request,
                'Formato no permitido. Use archivos XLSX, XLS, CSV u ODS.'
            )
            return redirect('inventario:lista_productos')

        # ============================================================
        # 3. LEER ARCHIVO
        # ============================================================

        if nombre_archivo.endswith('.csv'):
            try:
                df = pd.read_csv(
                    excel_file,
                    dtype=str,
                    sep=None,
                    engine='python'
                )
            except Exception:
                excel_file.seek(0)
                df = pd.read_csv(
                    excel_file,
                    dtype=str,
                    encoding='latin1',
                    sep=None,
                    engine='python'
                )

        elif nombre_archivo.endswith('.ods'):
            df = pd.read_excel(
                excel_file,
                engine='odf'
            )

        else:
            df = pd.read_excel(
                excel_file
            )

        # ============================================================
        # 4. VALIDAR QUE TENGA DATOS
        # ============================================================

        if df.empty:
            messages.error(
                request,
                'El archivo está vacío.'
            )
            return redirect('inventario:lista_productos')

        # ============================================================
        # 5. NORMALIZAR NOMBRES DE COLUMNAS
        # ============================================================

        def normalizar_texto(valor):
            if pd.isna(valor):
                return ''

            texto = str(valor).strip().lower()

            reemplazos = {
                'á': 'a',
                'é': 'e',
                'í': 'i',
                'ó': 'o',
                'ú': 'u',
                'ü': 'u',
                'ñ': 'n',
                '_': ' ',
                '-': ' ',
                '/': ' ',
            }

            for viejo, nuevo in reemplazos.items():
                texto = texto.replace(viejo, nuevo)

            texto = ' '.join(texto.split())

            return texto

        df.columns = [
            normalizar_texto(col)
            for col in df.columns
        ]

        # ============================================================
        # 6. DETECTAR COLUMNAS AUTOMÁTICAMENTE
        # ============================================================

        equivalencias = {
            'codigo_barras': [
                'codigo barras',
                'codigo de barras',
                'codigo',
                'cod',
                'cod barras',
                'barcode',
                'ean',
                'ean13',
                'ean 13',
                'upc',
                'referencia',
                'referencia producto',
                'sku',
            ],

            'descripcion': [
                'descripcion',
                'descripcion producto',
                'producto',
                'nombre',
                'nombre producto',
                'articulo',
                'articulo producto',
                'detalle',
            ],

            'stock_teorico': [
                'stock teorico',
                'stock',
                'cantidad',
                'cant',
                'existencia',
                'existencias',
                'inventario',
                'cantidad teorica',
                'cantidad esperada',
                'saldo',
            ],

            'ubicacion': [
                'ubicacion',
                'ubicacion fisica',
                'ubicacion producto',
                'zona',
                'sede',
                'bodega',
                'almacen',
                'almacenamiento',
                'localizacion',
                'rack',
            ],
        }

        columnas_detectadas = {}

        for campo, nombres_posibles in equivalencias.items():

            encontrada = None

            for columna in df.columns:
                if columna in nombres_posibles:
                    encontrada = columna
                    break

            if encontrada:
                columnas_detectadas[campo] = encontrada

        # ============================================================
        # 7. VALIDAR COLUMNAS OBLIGATORIAS
        # ============================================================

        obligatorias = {
            'codigo_barras',
            'descripcion',
        }

        faltantes = obligatorias - set(columnas_detectadas.keys())

        if faltantes:
            messages.error(
                request,
                'No fue posible identificar las columnas obligatorias: '
                + ', '.join(faltantes)
                + '. '
                'El archivo debe contener al menos código y descripción.'
            )
            return redirect('inventario:lista_productos')

        # ============================================================
        # 8. COLUMNAS OPCIONALES
        # ============================================================

        columna_codigo = columnas_detectadas['codigo_barras']
        columna_descripcion = columnas_detectadas['descripcion']

        columna_stock = columnas_detectadas.get('stock_teorico')
        columna_ubicacion = columnas_detectadas.get('ubicacion')

        # ============================================================
        # 9. PREPARAR DATOS
        # ============================================================

        productos_crear = []
        productos_actualizar = []

        codigos_db = set(
            Producto.objects.values_list(
                'codigo_barras',
                flat=True
            )
        )

        codigos_archivo = set()

        filas_ignoradas = 0
        filas_duplicadas = 0

        # ============================================================
        # 10. PROCESAR CADA FILA
        # ============================================================

        for index, row in df.iterrows():

            # --------------------------------------------------------
            # CÓDIGO
            # --------------------------------------------------------

            codigo_valor = row.get(columna_codigo, '')

            if pd.isna(codigo_valor):
                filas_ignoradas += 1
                continue

            codigo = str(codigo_valor).strip()

            # Eliminar .0 de Excel
            if codigo.endswith('.0'):
                codigo = codigo[:-2]

            # Eliminar espacios internos accidentales
            codigo = codigo.replace(' ', '')

            if not codigo:
                filas_ignoradas += 1
                continue

            # --------------------------------------------------------
            # DUPLICADOS DENTRO DEL MISMO ARCHIVO
            # --------------------------------------------------------

            if codigo in codigos_archivo:
                filas_duplicadas += 1
                continue

            codigos_archivo.add(codigo)

            # --------------------------------------------------------
            # DESCRIPCIÓN
            # --------------------------------------------------------

            descripcion_valor = row.get(
                columna_descripcion,
                ''
            )

            if pd.isna(descripcion_valor):
                descripcion = 'Sin descripción'
            else:
                descripcion = str(
                    descripcion_valor
                ).strip()

            if not descripcion:
                descripcion = 'Sin descripción'

            # --------------------------------------------------------
            # STOCK
            # --------------------------------------------------------

            stock = 0

            if columna_stock:
                stock_valor = row.get(
                    columna_stock,
                    0
                )

                try:
                    if pd.isna(stock_valor):
                        stock = 0
                    else:
                        stock = int(
                            float(
                                str(stock_valor)
                                .replace(',', '.')
                            )
                        )

                        if stock < 0:
                            stock = 0

                except (
                    ValueError,
                    TypeError,
                    OverflowError
                ):
                    stock = 0

            # --------------------------------------------------------
            # UBICACIÓN
            # --------------------------------------------------------

            ubicacion = None

            if columna_ubicacion:

                ubicacion_valor = row.get(
                    columna_ubicacion,
                    ''
                )

                if not pd.isna(ubicacion_valor):

                    ubicacion_texto = str(
                        ubicacion_valor
                    ).strip()

                    if ubicacion_texto:

                        ubicacion, _ = (
                            Ubicacion.objects.get_or_create(
                                codigo_barras=ubicacion_texto,
                                defaults={
                                    'rack': ubicacion_texto,
                                    'espacio': '',
                                    'nivel': '',
                                }
                            )
                        )

            # ========================================================
            # 11. ACTUALIZAR PRODUCTO EXISTENTE
            # ========================================================

            if codigo in codigos_db:

                try:
                    producto = Producto.objects.get(
                        codigo_barras=codigo
                    )

                    producto.descripcion = descripcion
                    producto.stock_teorico = stock
                    producto.ubicacion = ubicacion

                    productos_actualizar.append(
                        producto
                    )

                except Producto.DoesNotExist:
                    pass

                except Producto.MultipleObjectsReturned:
                    messages.warning(
                        request,
                        f'El código {codigo} está duplicado '
                        f'en la base de datos.'
                    )

            # ========================================================
            # 12. CREAR PRODUCTO NUEVO
            # ========================================================

            else:

                productos_crear.append(
                    Producto(
                        codigo_barras=codigo,
                        descripcion=descripcion,
                        stock_teorico=stock,
                        ubicacion=ubicacion,
                    )
                )

                codigos_db.add(codigo)

        # ============================================================
        # 13. GUARDAR NUEVOS
        # ============================================================

        if productos_crear:
            Producto.objects.bulk_create(
                productos_crear,
                batch_size=500
            )

        # ============================================================
        # 14. ACTUALIZAR EXISTENTES
        # ============================================================

        if productos_actualizar:
            Producto.objects.bulk_update(
                productos_actualizar,
                [
                    'descripcion',
                    'stock_teorico',
                    'ubicacion',
                ],
                batch_size=500
            )

        # ============================================================
        # 15. AUDITORÍA
        # ============================================================

        LogAuditoria.objects.create(
            usuario=request.user,
            accion='IMPORTAR',
            modelo='Producto',
            descripcion=(
                'Importación de productos. '
                f'Archivo: {excel_file.name}. '
                f'Base: {base_activa.nombre}. '
                f'Creados: {len(productos_crear)}. '
                f'Actualizados: {len(productos_actualizar)}. '
                f'Filas ignoradas: {filas_ignoradas}. '
                f'Duplicados: {filas_duplicadas}.'
            ),
            ip_direccion=get_client_ip(request)
        )

        # ============================================================
        # 16. MENSAJE FINAL
        # ============================================================

        messages.success(
            request,
            (
                f'Importación correcta. '
                f'{len(productos_crear)} productos creados y '
                f'{len(productos_actualizar)} actualizados.'
            )
        )

        if filas_ignoradas:
            messages.warning(
                request,
                f'Se ignoraron {filas_ignoradas} filas sin código.'
            )

        if filas_duplicadas:
            messages.warning(
                request,
                f'Se ignoraron {filas_duplicadas} códigos duplicados '
                f'dentro del archivo.'
            )

    except Exception as e:

        messages.error(
            request,
            f'Error al procesar el archivo: {str(e)}'
        )

    return redirect('inventario:lista_productos')


@login_required
def exportar_excel(request):
    producto_resource = ProductoResource()
    dataset = producto_resource.export()

    LogAuditoria.objects.create(
        usuario=request.user,
        accion='EXPORTAR',
        modelo='Producto',
        descripcion='Descarga del maestro general de productos en Excel',
        ip_direccion=get_client_ip(request)
    )

    response = HttpResponse(
        dataset.xlsx,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="maestro_productos.xlsx"'

    return response


@login_required
def crear_producto(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST)

        if form.is_valid():
            producto = form.save()

            LogAuditoria.objects.create(
                usuario=request.user,
                accion='CREAR',
                modelo='Producto',
                objeto_id=str(producto.id),
                descripcion=f'Creación manual de producto: {producto.codigo_barras}',
                ip_direccion=get_client_ip(request)
            )

            return redirect('inventario:lista_productos')
    else:
        form = ProductoForm()

    return render(
        request,
        'inventario/crear_producto.html',
        {
            'form': form
        }
    )