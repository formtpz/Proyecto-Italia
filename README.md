# Proyecto Italia — Sistema de reportes

Refactorización de la aplicación Streamlit para reportes de producción, eventos, historial, correcciones, RRHH y dashboards. Se eliminaron los módulos de asignaciones y el GeoJSON.

## Instalación

1. Crear **una base de datos PostgreSQL nueva**, separada de la BD de producción `bditalia`.
2. Ejecutar `sql/001_esquema_inicial.sql` en esa base nueva. Revisar los nombres de procesos iniciales.
3. Crear el usuario administrador inicial en `personal` (perfil 1). **La autenticación heredada utiliza contraseñas en texto plano; migrar a hashes antes de exponer la aplicación públicamente.**
4. Configurar `[db_credentials] URI = "postgresql://..."` en los secretos de Streamlit, apuntando exclusivamente a la nueva BD.
5. Instalar dependencias con `pip install -r requirements.txt` y ejecutar `streamlit run app.py`.

## Concurrencia

`db.py` mantiene una conexión PostgreSQL compartida **por proceso Python**, con `threading.RLock`. Todas las consultas usan `consultar`, `consultar_uno`, `leer_dataframe` o `transaccion`. El bloqueo abarca la transacción completa, incluido el commit/rollback; no se retiene durante la edición de formularios. Si Streamlit corre en varios procesos/instancias, cada proceso tendrá su propia conexión.

## Cambios

- No existen columnas de ubicación, región, zona ni complejidad en `reportes`.
- Los eventos omiten proceso y cantidades no aplicables; se almacenan como `NULL`.
- Los reportes de producción no requieren asignaciones.
- No se modifica `formtpz/bditalia` ni su base de datos.

**Antes del despliegue:** probar con la nueva BD los flujos de login, RRHH, producción, eventos, historial, correcciones y concurrencia. No desplegar durante captura activa de formularios.
