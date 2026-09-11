from django import forms
from .models import Producto, TransferenciaInventario, Ubicacion

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'codigo_barras',
            'descripcion',
            'stock_teorico',
            'ubicacion'
        ]
        widgets = {
            'codigo_barras': forms.TextInput(attrs={
                'class': 'w-full bg-slate-50 border border-slate-300 text-slate-900 text-sm rounded-lg focus:ring-boccherini-blue focus:border-boccherini-blue block p-2.5',
                'placeholder': 'Ej. 770123456789'
            }),
            'descripcion': forms.TextInput(attrs={
                'class': 'w-full bg-slate-50 border border-slate-300 text-slate-900 text-sm rounded-lg focus:ring-boccherini-blue focus:border-boccherini-blue block p-2.5',
                'placeholder': 'Ej. Ducha Eléctrica...'
            }),
            'stock_teorico': forms.NumberInput(attrs={
                'class': 'w-full bg-slate-50 border border-slate-300 text-slate-900 text-sm rounded-lg focus:ring-boccherini-blue focus:border-boccherini-blue block p-2.5',
                'placeholder': 'Ej. 100'
            }),
            'ubicacion': forms.Select(attrs={
                'class': 'w-full bg-slate-50 border border-slate-300 text-slate-900 text-sm rounded-lg focus:ring-boccherini-blue focus:border-boccherini-blue block p-2.5'
            }),
        }

class UbicacionForm(forms.ModelForm):

    class Meta:
        model = Ubicacion
        fields = [
            'codigo_barras',
            'rack',
            'espacio',
            'nivel',
        ]
        widgets = {
            'codigo_barras': forms.TextInput(attrs={
                'class': (
                    'w-full bg-slate-50 border border-slate-300 '
                    'text-slate-900 text-sm rounded-lg '
                    'focus:ring-boccherini-blue '
                    'focus:border-boccherini-blue block p-2.5'
                ),
                'placeholder': 'Ej. UB-R01-E03-N02',
            }),
            'rack': forms.TextInput(attrs={
                'class': (
                    'w-full bg-slate-50 border border-slate-300 '
                    'text-slate-900 text-sm rounded-lg '
                    'focus:ring-boccherini-blue '
                    'focus:border-boccherini-blue block p-2.5'
                ),
                'placeholder': 'Ej. R01',
            }),
            'espacio': forms.TextInput(attrs={
                'class': (
                    'w-full bg-slate-50 border border-slate-300 '
                    'text-slate-900 text-sm rounded-lg '
                    'focus:ring-boccherini-blue '
                    'focus:border-boccherini-blue block p-2.5'
                ),
                'placeholder': 'Ej. E03',
            }),
            'nivel': forms.TextInput(attrs={
                'class': (
                    'w-full bg-slate-50 border border-slate-300 '
                    'text-slate-900 text-sm rounded-lg '
                    'focus:ring-boccherini-blue '
                    'focus:border-boccherini-blue block p-2.5'
                ),
                'placeholder': 'Ej. N02',
            }),
        }

    def clean_codigo_barras(self):
        codigo = self.cleaned_data['codigo_barras'].strip()
        if not codigo:
            raise forms.ValidationError(
                'El código de barras de la ubicación es obligatorio.'
            )
        return codigo

    def clean(self):
        cleaned_data = super().clean()
        rack = cleaned_data.get('rack')
        espacio = cleaned_data.get('espacio')
        nivel = cleaned_data.get('nivel')

        if rack:
            cleaned_data['rack'] = rack.strip()
        if espacio:
            cleaned_data['espacio'] = espacio.strip()
        if nivel:
            cleaned_data['nivel'] = nivel.strip()

        return cleaned_data

class TransferenciaInventarioForm(forms.ModelForm):

    class Meta:
        model = TransferenciaInventario
        fields = [
            'producto',
            'cantidad',
            'ubicacion_origen',
            'ubicacion_destino',
            'motivo',
            'observacion',
        ]
        widgets = {
            'producto': forms.Select(attrs={
                'class': 'w-full bg-slate-50 border border-slate-300 text-slate-900 text-sm rounded-lg focus:ring-boccherini-blue focus:border-boccherini-blue block p-2.5'
            }),
            'cantidad': forms.NumberInput(attrs={
                'class': 'w-full bg-slate-50 border border-slate-300 text-slate-900 text-sm rounded-lg focus:ring-boccherini-blue focus:border-boccherini-blue block p-2.5',
                'min': 1,
            }),
            'ubicacion_origen': forms.Select(attrs={
                'class': 'w-full bg-slate-50 border border-slate-300 text-slate-900 text-sm rounded-lg focus:ring-boccherini-blue focus:border-boccherini-blue block p-2.5'
            }),
            'ubicacion_destino': forms.Select(attrs={
                'class': 'w-full bg-slate-50 border border-slate-300 text-slate-900 text-sm rounded-lg focus:ring-boccherini-blue focus:border-boccherini-blue block p-2.5'
            }),
            'motivo': forms.TextInput(attrs={
                'class': 'w-full bg-slate-50 border border-slate-300 text-slate-900 text-sm rounded-lg focus:ring-boccherini-blue focus:border-boccherini-blue block p-2.5',
                'placeholder': 'Motivo de la transferencia'
            }),
            'observacion': forms.Textarea(attrs={
                'class': 'w-full bg-slate-50 border border-slate-300 text-slate-900 text-sm rounded-lg focus:ring-boccherini-blue focus:border-boccherini-blue block p-2.5',
                'rows': 3,
                'placeholder': 'Observaciones adicionales'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()

        origen = cleaned_data.get('ubicacion_origen')
        destino = cleaned_data.get('ubicacion_destino')
        cantidad = cleaned_data.get('cantidad')

        if origen and destino and origen == destino:
            raise forms.ValidationError(
                'La ubicación de origen y destino deben ser diferentes.'
            )

        if cantidad is not None and cantidad <= 0:
            raise forms.ValidationError(
                'La cantidad debe ser mayor que cero.'
            )

        return cleaned_data