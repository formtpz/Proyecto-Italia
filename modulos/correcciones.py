import streamlit as st
from datetime import datetime
from psycopg2 import sql
from db import leer_dataframe, transaccion
from permisos import validar_acceso

COLUMNAS_EDITABLES = ("fecha_reporte", "horas", "produccion", "aprobados", "rechazados", "observaciones")

def render():
    validar_acceso("Correcciones")
    usuario = st.session_state["usuario"]
    perfil = usuario["perfil"]
    st.title("🛠️ Correcciones de Reportes")

    if perfil in (3, 4):
        st.subheader("📋 Registros")
        c1, c2 = st.columns(2)
        with c1:
            inicio = st.date_input("Desde")
        with c2:
            fin = st.date_input("Hasta")
        df = leer_dataframe("""
            SELECT id, fecha_reporte, cedula_personal, horas, produccion,
                   aprobados, rechazados, observaciones
            FROM reportes
            WHERE fecha_reporte BETWEEN %s AND %s AND cedula_personal = %s
            ORDER BY fecha_reporte DESC
        """, (inicio, fin, usuario["cedula"]))
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.subheader("✏️ Solicitar corrección")
        with st.form("form_solicitud"):
            id_reporte = st.number_input("ID del reporte", min_value=1, step=1)
            columna = st.selectbox("Columna con error", COLUMNAS_EDITABLES)
            nuevo_valor = st.text_input("Nuevo valor correcto")
            solucion = st.selectbox("Tipo de acción", ["Modificar", "Eliminar"])
            detalle = st.text_area("Detalle del error")
            enviar = st.form_submit_button("📨 Enviar solicitud")
        if enviar:
            try:
                with transaccion() as cur:
                    cur.execute("""
                        INSERT INTO correcciones (
                            cedula, nombre, fecha, id_asociado, tipo_error,
                            solucion, tabla, columna, nuevo_valor, estado
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (usuario["cedula"], usuario["nombre"], datetime.now(),
                          int(id_reporte), columna, solucion, "reportes",
                          columna, nuevo_valor or None, "pendiente"))
                st.success("Solicitud registrada")
            except Exception as exc:
                st.error(f"No fue posible registrar la solicitud: {exc}")
        st.subheader("📜 Mis solicitudes")
        st.dataframe(leer_dataframe("""
            SELECT fecha, id_asociado, columna, solucion, estado
            FROM correcciones WHERE cedula = %s ORDER BY fecha DESC
        """, (usuario["cedula"],)), use_container_width=True, hide_index=True)

    elif perfil == 1:
        st.subheader("🧾 Correcciones pendientes")
        df = leer_dataframe("""
            SELECT id, fecha, cedula, nombre, id_asociado, columna,
                   nuevo_valor, solucion, estado
            FROM correcciones WHERE estado = 'pendiente' ORDER BY fecha
        """)
        if not df.empty:
            editado = st.data_editor(
                df, key="editor_correcciones", num_rows="fixed",
                disabled=[c for c in df.columns if c != "estado"],
                column_config={"estado": st.column_config.SelectboxColumn(
                    "Estado", options=["pendiente", "corregido"])},
                hide_index=True)
            if st.button("💾 Guardar estados"):
                try:
                    with transaccion() as cur:
                        for _, fila in editado.iterrows():
                            cur.execute("UPDATE correcciones SET estado=%s WHERE id=%s",
                                        (fila["estado"], int(fila["id"])))
                    st.success("Estados actualizados")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        else:
            st.info("No hay correcciones pendientes")

        st.subheader("📊 Reportes asociados")
        ids = df["id_asociado"].dropna().astype(int).unique().tolist() if not df.empty else []
        if ids:
            reportes = leer_dataframe("SELECT * FROM reportes WHERE id = ANY(%s) ORDER BY id", (ids,))
            editados = st.data_editor(reportes, key="editor_reportes", num_rows="fixed",
                                      disabled=["id"], hide_index=True)
            if st.button("💾 Guardar cambios en reportes"):
                try:
                    with transaccion() as cur:
                        for _, fila in editados.iterrows():
                            for columna in COLUMNAS_EDITABLES:
                                if columna in editados.columns:
                                    valor = fila[columna]
                                    if hasattr(valor, "item"):
                                        valor = valor.item()
                                    if valor != valor:
                                        valor = None
                                    cur.execute(sql.SQL("UPDATE reportes SET {}=%s WHERE id=%s").format(
                                        sql.Identifier(columna)), (valor, int(fila["id"])))
                    st.success("Reportes actualizados")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

        st.subheader("🗑️ Eliminar reporte manualmente")
        id_eliminar = st.number_input("ID del reporte a eliminar", min_value=1, step=1)
        confirmar = st.checkbox("Confirmo la eliminación permanente")
        if st.button("🚨 Eliminar definitivamente", disabled=not confirmar):
            try:
                with transaccion() as cur:
                    cur.execute("DELETE FROM reportes WHERE id = %s", (int(id_eliminar),))
                st.success("Reporte eliminado")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
