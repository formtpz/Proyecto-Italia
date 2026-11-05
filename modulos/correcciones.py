"""Solicitudes de corrección de reportes. Todas las consultas usan el schema italia vía db.py."""
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import streamlit as st
from psycopg2 import sql
from db import consultar_uno, leer_dataframe, transaccion
from permisos import validar_acceso

DIAS_SOLICITUD = 3
COLUMNAS_EDITABLES = {
    "fecha_reporte": "Fecha del reporte",
    "horas": "Horas",
    "tipo_produccion": "Tipo de producción",
    "produccion": "Cantidad producida",
    "aprobados": "Aprobados",
    "rechazados": "Rechazados",
    "estado": "Estado de producción",
    "observaciones": "Observaciones",
    "tipo_evento_id": "Tipo de evento",
}
COL_PRODUCCION = ("fecha_reporte", "horas", "tipo_produccion", "produccion",
                  "aprobados", "rechazados", "estado", "observaciones")
COL_EVENTO = ("fecha_reporte", "horas", "tipo_evento_id", "observaciones")
ESTADOS = ("pendiente", "corregido")


def _opciones_columnas(tipo):
    columnas = COL_EVENTO if tipo == "evento" else COL_PRODUCCION
    return {COLUMNAS_EDITABLES[col]: col for col in columnas}


def _validar_valor(columna, valor):
    if valor is None or not str(valor).strip():
        if columna in ("tipo_produccion", "observaciones", "estado",
                       "produccion", "aprobados", "rechazados"):
            return None
        raise ValueError("El nuevo valor no puede estar vacío para esta columna.")
    texto = str(valor).strip()
    if columna == "fecha_reporte":
        try:
            return date.fromisoformat(texto)
        except ValueError as exc:
            raise ValueError("La fecha debe tener formato AAAA-MM-DD.") from exc
    if columna == "horas":
        try:
            numero = Decimal(texto.replace(",", "."))
        except InvalidOperation as exc:
            raise ValueError("Horas debe ser un número decimal válido.") from exc
        if not numero.is_finite() or numero < 0 or numero > 24:
            raise ValueError("Horas debe estar entre 0 y 24.")
        return numero
    if columna in ("produccion", "aprobados", "rechazados", "tipo_evento_id"):
        try:
            entero = int(texto)
        except ValueError as exc:
            raise ValueError("El valor debe ser un número entero.") from exc
        if entero < 0 or (columna == "tipo_evento_id" and entero > 16):
            raise ValueError("El valor indicado está fuera del rango permitido.")
        return entero
    if columna == "tipo_produccion" and len(texto) > 200:
        raise ValueError("Tipo de producción admite hasta 200 caracteres.")
    if columna == "estado" and len(texto) > 50:
        raise ValueError("El estado admite hasta 50 caracteres.")
    return texto


def _solicitar(usuario):
    cedula = usuario["cedula"]
    nombre = usuario["nombre"]
    st.subheader("Mis reportes recientes")
    st.caption("Puedes solicitar una corrección durante los 3 días posteriores a la fecha del reporte.")
    limite = date.today() - timedelta(days=DIAS_SOLICITUD)
    reportes = leer_dataframe("""
        SELECT id, fecha_reporte, tipo_reporte, horas, tipo_produccion,
               produccion, aprobados, rechazados, tipo_evento_id,
               estado, observaciones
        FROM reportes
        WHERE cedula_personal = %s AND fecha_reporte >= %s
        ORDER BY fecha_reporte DESC, id DESC
    """, (cedula, limite))
    if reportes.empty:
        st.info("No tienes reportes dentro del plazo de solicitud.")
    else:
        st.dataframe(reportes, use_container_width=True, hide_index=True)

        opciones = {
            f"#{int(fila.id)} — {fila.fecha_reporte} — {fila.tipo_reporte}": int(fila.id)
            for fila in reportes.itertuples()
        }
        with st.form("nueva_solicitud_correccion", clear_on_submit=True):
            seleccionado = st.selectbox("Reporte a corregir", list(opciones))
            accion = st.radio("Tipo de solicitud", ("Modificar", "Eliminar"),
                              horizontal=True)
            detalle = st.text_area("Motivo de la solicitud")
            crear = st.form_submit_button("Registrar solicitud")
        if crear:
            try:
                reporte_id = opciones[seleccionado]
                with transaccion() as cur:
                    cur.execute("""
                        SELECT id, tipo_reporte FROM reportes
                        WHERE id = %s AND cedula_personal = %s
                          AND fecha_reporte >= %s FOR UPDATE
                    """, (reporte_id, cedula, limite))
                    reporte = cur.fetchone()
                    if not reporte:
                        raise ValueError("El reporte no existe, no es tuyo o está fuera del plazo.")
                    cur.execute("""
                        SELECT id FROM correcciones WHERE id_asociado = %s
                          AND estado = 'pendiente' FOR UPDATE
                    """, (reporte_id,))
                    if cur.fetchone():
                        raise ValueError("Ya existe una solicitud pendiente para este reporte.")
                    cur.execute("""
                        INSERT INTO correcciones
                          (cedula, nombre, id_asociado, tipo_error, solucion,
                           tabla, columna, nuevo_valor, estado)
                        VALUES (%s, %s, %s, %s, %s, 'reportes', NULL, NULL, 'pendiente')
                    """, (cedula, nombre, reporte_id,
                          detalle.strip() or "Pendiente de detalle", accion))
                st.success("Solicitud registrada. Completa los detalles más abajo.")
                st.rerun()
            except Exception as exc:
                st.error(f"No fue posible crear la solicitud: {exc}")

    st.subheader("Gestionar mis solicitudes pendientes")
    pendientes = leer_dataframe("""
        SELECT c.id, c.fecha, c.id_asociado, r.tipo_reporte,
               c.solucion, c.tipo_error, c.columna, c.nuevo_valor
        FROM correcciones c
        JOIN reportes r ON r.id = c.id_asociado
        WHERE c.cedula = %s AND c.estado = 'pendiente'
        ORDER BY c.fecha DESC
    """, (cedula,))
    if pendientes.empty:
        st.info("No tienes solicitudes pendientes.")
    else:
        opciones = {
            f"Solicitud #{int(fila.id)} — Reporte #{int(fila.id_asociado)}":
                int(fila.id) for fila in pendientes.itertuples()
        }
        st.subheader("Editar una solicitud")
        seleccion = st.selectbox("Solicitud que deseas editar", list(opciones),
                                 key="solicitud_pendiente")
        fila = pendientes.loc[pendientes["id"] == opciones[seleccion]].iloc[0]
        columnas = _opciones_columnas(fila["tipo_reporte"])
        inverso = {v: k for k, v in columnas.items()}
        actual = inverso.get(fila["columna"])
        with st.form(f"editar_solicitud_{int(fila['id'])}"):
            accion = st.radio("Acción solicitada", ("Modificar", "Eliminar"),
                              index=0 if fila["solucion"] == "Modificar" else 1)
            columna_label = st.selectbox("Campo a modificar",
                                          list(columnas),
                                          index=list(columnas).index(actual) if actual else 0,
                                          help="Se ignora si la acción es Eliminar.")
            valor = st.text_input("Nuevo valor (fecha: AAAA-MM-DD; horas: decimal)",
                                   value=str(fila["nuevo_valor"]) if fila["nuevo_valor"] is not None else "")
            motivo = st.text_area("Motivo", value=fila["tipo_error"] or "")
            guardar = st.form_submit_button("Guardar cambios de la solicitud")
        if guardar:
            try:
                columna = columnas[columna_label] if accion == "Modificar" else None
                if accion == "Modificar":
                    _validar_valor(columna, valor)
                with transaccion() as cur:
                    cur.execute("""
                        UPDATE correcciones
                           SET solucion=%s, columna=%s, nuevo_valor=%s, tipo_error=%s
                         WHERE id=%s AND cedula=%s AND estado='pendiente'
                    """, (accion, columna, valor.strip() if columna else None,
                          motivo.strip() or "Sin detalle", int(fila["id"]), cedula))
                    if cur.rowcount != 1:
                        raise ValueError("La solicitud ya no está pendiente o no te pertenece.")
                st.success("Solicitud actualizada.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))


        st.divider()
        st.subheader("Cancelar solicitudes pendientes")
        st.caption("Selecciona una o varias solicitudes para cancelarlas. Los reportes originales no se eliminan.")
        opciones_cancelacion = {
            f"Solicitud #{int(fila.id)} | Reporte #{int(fila.id_asociado)} | {fila.solucion}":
                int(fila.id) for fila in pendientes.itertuples()
        }
        with st.form("cancelar_solicitudes_pendientes"):
            seleccion_cancelar = st.multiselect(
                "Solicitudes que deseas cancelar",
                options=list(opciones_cancelacion),
                key="seleccion_cancelar_solicitudes",
            )
            confirmar_cancelacion = st.checkbox(
                "Confirmo que deseo cancelar las solicitudes seleccionadas"
            )
            cancelar = st.form_submit_button("Cancelar solicitudes seleccionadas")
        if cancelar:
            if not seleccion_cancelar:
                st.warning("Selecciona al menos una solicitud.")
            elif not confirmar_cancelacion:
                st.warning("Marca la confirmación.")
            else:
                ids_cancelar = [opciones_cancelacion[x] for x in seleccion_cancelar]
                try:
                    with transaccion() as cur:
                        cur.execute("""
                            UPDATE correcciones
                               SET estado='cancelada'
                             WHERE id = ANY(%s) AND cedula=%s AND estado='pendiente'
                        """, (ids_cancelar, cedula))
                        cantidad = cur.rowcount
                    st.success(
                        f"{cantidad} solicitud(es) cancelada(s). "
                        "Permanecen en el historial y los reportes originales no cambian."
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"No fue posible cancelar las solicitudes: {exc}")

    st.subheader("Historial de mis solicitudes")
    historico = leer_dataframe("""
        SELECT id, fecha, id_asociado, solucion, columna, nuevo_valor,
               tipo_error AS motivo, estado
        FROM correcciones WHERE cedula=%s ORDER BY fecha DESC
    """, (cedula,))
    st.dataframe(historico, use_container_width=True, hide_index=True)


def _coordinar():
    st.subheader("Gestión de solicitudes")
    filtro = st.selectbox("Mostrar solicitudes", ("Pendientes", "Todas"))
    where = "WHERE c.estado='pendiente'" if filtro == "Pendientes" else ""
    solicitudes = leer_dataframe(f"""
        SELECT c.id, c.fecha, c.cedula, c.nombre, c.id_asociado,
               r.tipo_reporte, c.solucion, c.columna, c.nuevo_valor,
               c.tipo_error AS motivo, c.estado, c.procesado_por, c.procesado_en
        FROM correcciones c
        LEFT JOIN reportes r ON r.id=c.id_asociado
        {where}
        ORDER BY c.fecha DESC
    """)
    st.dataframe(solicitudes, use_container_width=True, hide_index=True)
    st.subheader("Resumen de solicitudes por persona")
    resumen = leer_dataframe("""
        SELECT cedula, nombre,
               COUNT(*) AS total_solicitudes,
               COUNT(*) FILTER (WHERE solucion='Modificar') AS modificaciones,
               COUNT(*) FILTER (WHERE solucion='Eliminar') AS eliminaciones,
               COUNT(*) FILTER (WHERE estado='corregido') AS aplicadas,
               COUNT(*) FILTER (WHERE estado='cancelada') AS canceladas,
               COUNT(*) FILTER (WHERE estado='rechazada') AS rechazadas
        FROM correcciones
        GROUP BY cedula, nombre
        ORDER BY total_solicitudes DESC, nombre
    """)
    st.dataframe(resumen, use_container_width=True, hide_index=True)
    if solicitudes.empty:
        st.info("No hay solicitudes para el filtro seleccionado.")
        return

    opciones = {
        f"Solicitud #{int(fila.id)} — Reporte #{int(fila.id_asociado)} ({fila.nombre})":
            int(fila.id) for fila in solicitudes.itertuples()
    }
    seleccion = st.selectbox("Seleccionar solicitud", list(opciones))
    solicitud_id = opciones[seleccion]
    fila = solicitudes.loc[solicitudes["id"] == solicitud_id].iloc[0]

    reporte = leer_dataframe("SELECT * FROM reportes WHERE id=%s",
                              (int(fila["id_asociado"]),))
    st.subheader("Reporte original")
    st.dataframe(reporte, use_container_width=True, hide_index=True)

    if fila["estado"] != "pendiente":
        st.info("Esta solicitud ya fue procesada.")
        return

    if fila["solucion"] == "Modificar":
        if not fila["columna"]:
            st.warning("El solicitante aún no ha indicado la columna a modificar.")
            return
        st.info(f"Modificación solicitada: {fila['columna']} → {fila['nuevo_valor']}")
    else:
        st.warning("Se solicita la eliminación permanente del reporte original.")

    with st.form(f"procesar_solicitud_{solicitud_id}"):
        aplicar = st.checkbox("Confirmo que revisé el reporte y deseo aplicar la solicitud")
        enviar = st.form_submit_button("Aplicar y marcar como corregida")
    if enviar:
        if not aplicar:
            st.error("Confirma que revisaste el reporte antes de aplicar.")
            return
        try:
            with transaccion() as cur:
                cur.execute("""
                    SELECT c.id, c.id_asociado, c.solucion, c.columna, c.nuevo_valor,
                           r.tipo_reporte, r.cedula_personal
                      FROM correcciones c
                      JOIN reportes r ON r.id = c.id_asociado
                     WHERE c.id=%s AND c.estado='pendiente'
                       FOR UPDATE OF c, r
                """, (solicitud_id,))
                datos = cur.fetchone()
                if datos is None:
                    raise ValueError("Esta solicitud ya no está pendiente o el reporte fue eliminado.")
                _, reporte_id, accion, columna, valor, tipo, cedula_personal = datos
                if accion == "Eliminar":
                    cur.execute("DELETE FROM reportes WHERE id=%s", (reporte_id,))
                    cur.execute("""
                        UPDATE correcciones
                        SET estado='corregido', procesado_por=%s, procesado_en=NOW()
                        WHERE id=%s AND estado='pendiente'
                    """, (st.session_state["usuario"]["cedula"], solicitud_id))
                elif accion == "Modificar":
                    if columna not in _opciones_columnas(tipo).values():
                        raise ValueError("La columna solicitada no está permitida para este tipo de reporte.")
                    nuevo = _validar_valor(columna, valor)
                    if columna == "tipo_evento_id":
                        cur.execute("SELECT 1 FROM tipos_evento WHERE id=%s", (nuevo,))
                        if cur.fetchone() is None:
                            raise ValueError("El tipo de evento indicado no existe.")
                    cur.execute(sql.SQL("UPDATE reportes SET {}=%s WHERE id=%s").format(
                        sql.Identifier(columna)), (nuevo, reporte_id))
                    cur.execute("""
                        UPDATE correcciones
                        SET estado='corregido', procesado_por=%s, procesado_en=NOW()
                        WHERE id=%s AND estado='pendiente'
                    """, (st.session_state["usuario"]["cedula"], solicitud_id))
                else:
                    raise ValueError("Tipo de solicitud no reconocido.")
            st.success("Solicitud aplicada correctamente.")
            st.rerun()
        except Exception as exc:
            st.error(f"No fue posible aplicar la solicitud: {exc}")


def render():
    validar_acceso("Correcciones")
    usuario = st.session_state["usuario"]
    st.title("🛠️ Solicitudes de corrección")
    if usuario["perfil"] == 1:
        _coordinar()
    elif usuario["perfil"] in (3, 4, 5):
        _solicitar(usuario)
    else:
        st.error("No tiene permiso para utilizar este módulo.")
        st.stop()
