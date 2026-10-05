Registro técnico — Conexión MySQL desde Docker

Fecha: 05/10/2026
Proyecto: Sistema Inventario
Django: 5.2.17
Base de datos: MySQL

Problema identificado:
Al ejecutar el sistema dentro del contenedor Docker, el login generaba error 500 porque Django intentaba conectarse a MySQL utilizando:

DB_HOST=127.0.0.1

Dentro de Docker, 127.0.0.1 hace referencia al propio contenedor, no al equipo Windows donde está ejecutándose MySQL.

Diagnóstico confirmado:
El error fue:

OperationalError: Can't connect to server on '127.0.0.1'

Se realizó una prueba utilizando:

DB_HOST=host.docker.internal

y se confirmó la conexión:

DB OK

Posteriormente se levantó el sistema mediante Gunicorn con:

docker run --rm --env-file .env -e DB_HOST=host.docker.internal -p 8004:8000 sistema-inventario:prueba gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 1 --timeout 30 --access-logfile -

Resultado:
✅ Sistema cargó correctamente.
✅ Login funcionando.
✅ Conexión Docker → MySQL funcionando.
✅ No fue necesario modificar el código Django.

Consideración para producción

No se debe asumir que host.docker.internal será el valor definitivo del servidor.

Ese valor corresponde a la prueba actual donde:

Docker → Windows → MySQL

Cuando el sistema se despliegue en el servidor, DB_HOST deberá apuntar al host real de MySQL, al nombre del servicio Docker, o a la dirección correspondiente según la arquitectura definitiva.

Conclusión: el código de autenticación y la configuración Django de conexión funcionan; el problema encontrado fue de direccionamiento de la base de datos dentro del entorno Docker.