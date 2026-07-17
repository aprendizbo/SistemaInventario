from django import forms
from .models import Producto

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'codigo_barras',
            'descripcion',
            'stock_teorico',
            'rack',
            'espacio',
            'nivel'
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
            'rack': forms.TextInput(attrs={
                'class': 'w-full bg-slate-50 border border-slate-300 text-slate-900 text-sm rounded-lg focus:ring-boccherini-blue focus:border-boccherini-blue block p-2.5',
                'placeholder': 'Ej. Rack 01'
            }),
            'espacio': forms.TextInput(attrs={
                'class': 'w-full bg-slate-50 border border-slate-300 text-slate-900 text-sm rounded-lg focus:ring-boccherini-blue focus:border-boccherini-blue block p-2.5',
                'placeholder': 'Ej. A1'
            }),
            'nivel': forms.TextInput(attrs={
                'class': 'w-full bg-slate-50 border border-slate-300 text-slate-900 text-sm rounded-lg focus:ring-boccherini-blue focus:border-boccherini-blue block p-2.5',
                'placeholder': 'Ej. 01'
            }),
        }