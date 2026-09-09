warning: in the working copy of 'inventario/views/__init__.py', LF will be replaced by CRLF the next time Git touches it
[1mdiff --git a/inventario/templates/inventario/base.html b/inventario/templates/inventario/base.html[m
[1mindex f23267b..b5c4b7a 100644[m
[1m--- a/inventario/templates/inventario/base.html[m
[1m+++ b/inventario/templates/inventario/base.html[m
[36m@@ -396,6 +396,54 @@[m
                     {% endif %}[m
 [m
 [m
[32m+[m[32m                    <!-- AUDITORÍA -->[m
[32m+[m
[32m+[m[32m                    <a[m
[32m+[m[32m                        href="{% url 'inventario:historial_auditoria' %}"[m
[32m+[m[32m                        class="[m
[32m+[m[32m                            block[m
[32m+[m[32m                            border[m
[32m+[m[32m                            border-slate-200[m
[32m+[m[32m                            rounded-xl[m
[32m+[m[32m                            p-4[m
[32m+[m[32m                            hover:border-boccherini-gold[m
[32m+[m[32m                            hover:shadow-md[m
[32m+[m[32m                            transition-all[m
[32m+[m[32m                            bg-slate-50[m
[32m+[m[32m                            cursor-pointer[m
[32m+[m[32m                        "[m
[32m+[m[32m                    >[m
[32m+[m
[32m+[m[32m                        <h4 class="font-bold text-slate-800 text-md mb-1">[m
[32m+[m[32m                            📋 Auditoría del Sistema[m
[32m+[m[32m                        </h4>[m
[32m+[m
[32m+[m[32m                        <p class="text-xs text-slate-500 mb-4">[m
[32m+[m[32m                            Consultar la trazabilidad y el historial de operaciones del sistema.[m
[32m+[m[32m                        </p>[m
[32m+[m
[32m+[m[32m                        <span[m
[32m+[m[32m                            class="[m
[32m+[m[32m                                inline-block[m
[32m+[m[32m                                text-center[m
[32m+[m[32m                                text-xs[m
[32m+[m[32m                                font-bold[m
[32m+[m[32m                                text-white[m
[32m+[m[32m                                bg-blue-600[m
[32m+[m[32m                                py-2[m
[32m+[m[32m                                px-3[m
[32m+[m[32m                                rounded-lg[m
[32m+[m[32m                                w-full[m
[32m+[m[32m                                transition-colors[m
[32m+[m[32m                                hover:bg-blue-700[m
[32m+[m[32m                            "[m
[32m+[m[32m                        >[m
[32m+[m[32m                            Ver Auditoría[m
[32m+[m[32m                        </span>[m
[32m+[m
[32m+[m[32m                    </a>[m
[32m+[m
[32m+[m
                     <!-- CERRAR SISTEMA -->[m
 [m
                     <form[m
[1mdiff --git a/inventario/views/__init__.py b/inventario/views/__init__.py[m
[1mindex 8279b0e..68a720a 100644[m
[1m--- a/inventario/views/__init__.py[m
[1m+++ b/inventario/views/__init__.py[m
[36m@@ -1,4 +1,4 @@[m
[31m-from .sesiones import ([m
[32m+[m[32m﻿from .sesiones import ([m
     panel_sesiones,[m
     crear_sesion,[m
     cerrar_sesion,[m
[36m@@ -34,6 +34,9 @@[m [mfrom .usuarios import ([m
     crear_usuario,[m
     cambiar_password_usuario,[m
     toggle_usuario,[m
[32m+[m[32m)[m
[32m+[m
[32m+[m[32mfrom .auditoria import ([m
     historial_auditoria,[m
 )[m
 [m
[36m@@ -41,4 +44,4 @@[m [mfrom .bases import ([m
     bases_productos,[m
     crear_base_inventario,[m
     cerrar_base_inventario,[m
[31m-)[m
\ No newline at end of file[m
[32m+[m[32m)[m
