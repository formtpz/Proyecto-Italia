import streamlit as st
import pandas as pd
from datetime import datetime
from db import leer_dataframe, transaccion
from permisos import validar_acceso


def render():
    validar_acceso("Correcciones")

    usuario = st.session_state["usuario"]
    perfil = usuario["perfil"]
    cedula = usuario["cedula"]


    st.title("🛠️ Correcciones de Reportes")

    # =====================================================
    # PERFIL 3 y 4 → SOLICITUD
    # =====================================================
    if perfil == 3 or perfil == 4:
        st.subheader("📋 Registros")

        col1, col2 = st.columns(2)
        with col1:
            fecha_inicio = st.date_input("Desde")
        with col2:
            fecha_fin = st.date_input("Hasta")

        df_registros = leer_dataframe("""
            SELECT
                id,
                fecha_reporte,
                cedula_personal,
                horas,
                produccion,
                aprobados,
                rechazados,
                observaciones
            FROM reportes
            WHERE fecha_reporte BETWEEN %s AND %s 
              AND cedula_personal = %s
            ORDER BY fecha_reporte DESC
        """, params=[fecha_inicio, fecha_fin, cedula])

        st.info("Seleccione visualmente el registro con error y copie el ID")
        st.dataframe(df_registros, use_container_width=True)

        st.divider()

        # =====================================================
        # ✏️ SOLICITUD DE CORRECCIÓN
        # =====================================================
        st.subheader("✏️ Solicitar corrección")

        columnas_reportes = [
            "fecha_reporte",
            "horas",
            "produccion",
            "aprobados",
            "rechazados",
            "observaciones"
        ]

        with st.form("form_solicitud"):
            id_asociado = st.text_input(
                "ID del reporte",
                help="Copie el ID desde la tabla de registros"
            )

            columna = st.selectbox(
                "Columna con error",
                columnas_reportes
            )

            nuevo_valor = st.text_input("Nuevo valor correcto")

            solucion = st.selectbox(
                "Tipo de acción",
                ["Modificar", "Eliminar"]
            )

            detalle = st.text_area("Detalle del error")

            submit = st.form_submit_button("📨 Enviar solicitud")

        if submit:
                    with transaccion() as cur:
                        cur.execute("""
                    INSERT INTO correcciones (
                        cedula,
                        nombre,
                        fecha,
                        id_asociado,
                        tipo_error,
                        solucion,
                        tabla,
                        columna,
                        nuevo_valor,
                        estado
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    usuario["cedula"],
                    usuario["nombre"],
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    id_asociado,
                    columna,
                    solucion,
                    "reportes",
                    columna,
                    nuevo_valor,
                    "pendiente"
                ))
            st.success("✅ Solicitud registrada correctamente")

        st.divider()

        # =====================================================
        # 📜 HISTORIAL DE SOLICITUDES
        # =====================================================
        st.subheader("📜 Mis solicitudes")

        df = leer_dataframe("""
            SELECT
                fecha,
                id_asociado,
                columna,
                solucion,
                estado
            FROM correcciones
            WHERE cedula = %s
            ORDER BY fecha DESC
        """, params=[usuario["cedula"]])

        st.dataframe(df, use_container_width=True)

    # =====================================================
    # PERFIL 1 → ADMIN
    # =====================================================
    elif perfil == 1:

        st.subheader("🧾 Correcciones pendientes")

        # =====================================================
        # TABLA 1: CORRECCIONES
        # =====================================================
        df_corr = leer_dataframe("""
            SELECT
                id,
                fecha,
                cedula,
                nombre,
                id_asociado,
                columna,
                nuevo_valor,
                solucion,
                estado
            FROM correcciones
            WHERE estado = 'pendiente'
            ORDER BY fecha
        """)

        if df_corr.empty:
            st.info("No hay correcciones pendientes")
            return

        df_corr_edit = st.data_editor(
            df_corr,
            use_container_width=True,
            num_rows="fixed",
            column_config={
                "estado": st.column_config.SelectboxColumn(
                    "estado",
                    options=["pendiente", "corregido"]
                )
            },
            disabled=[
                "id",
                "fecha",
                "cedula",
                "nombre",
                "id_asociado",
                "columna",
                "nuevo_valor",
                "solucion"
            ],
            key="editor_correcciones",
            hide_index=True
        )

        if st.button("💾 Guardar cambios de correcciones"):
                    for _, row in df_corr_edit.iterrows():
                with transaccion() as cur:
                    cur.execute("""
                        UPDATE correcciones
                        SET estado = %s
                        WHERE id = %s
                    """, (row["estado"], int(row["id"])))
            st.success("✅ Estados actualizados")
            st.rerun()

        st.divider()

        # =====================================================
        # TABLA 2: REPORTES ASOCIADOS
        # =====================================================
        st.subheader("📊 Reportes asociados")

        ids_reportes = df_corr["id_asociado"].astype(int).unique().tolist()

        df_rep = leer_dataframe("""
            SELECT *
            FROM reportes
            WHERE id = ANY(%s)
            ORDER BY id
        """, params=[ids_reportes])

        if df_rep.empty:
            st.info("No hay reportes asociados")
            return

        df_rep_edit = st.data_editor(
            df_rep,
            use_container_width=True,
            num_rows="fixed",
            disabled=["id"],
            key="editor_reportes",
            hide_index=True
        )

        if st.button("💾 Guardar cambios en reportes"):
        
            columnas = [c for c in df_rep_edit.columns if c != "id"]

            for _, row in df_rep_edit.iterrows():
                set_clause = ", ".join([f"{c} = %s" for c in columnas])
                valores = [row[c] for c in columnas]
                valores.append(int(row["id"]))

                with transaccion() as cur:
                    cur.execute(
                        f"UPDATE reportes SET {set_clause} WHERE id = %s",
                        valores
                    )
    
            st.success("✅ Reportes actualizados correctamente")
            st.rerun()

        st.divider()

        # =====================================================
        # ELIMINAR REPORTE MANUALMENTE
        # =====================================================
        st.subheader("🗑️ Eliminar reporte manualmente")

        id_eliminar = st.text_input(
            "Ingrese el ID del reporte a eliminar",
            key="input_id_eliminar"
        )

        if id_eliminar:
            try:
                df_ver = leer_dataframe("""
                    SELECT *
                    FROM reportes
                    WHERE id = %s
                """, params=[int(id_eliminar)])

                if df_ver.empty:
                    st.warning("No existe un reporte con ese ID")
                else:
                    st.warning("⚠️ Verifique cuidadosamente antes de eliminar")
                    st.dataframe(df_ver, use_container_width=True)

                    confirmar = st.checkbox(
                        "Confirmo que deseo eliminar este reporte permanentemente"
                    )

                    if confirmar:
                        if st.button("🚨 Eliminar definitivamente"):
                                                    with transaccion() as cur:
                                                        cur.execute("""
                                    DELETE FROM reportes
                                    WHERE id = %s
                                """, (int(id_eliminar),))
    
                            st.success("✅ Reporte eliminado correctamente")
                            st.rerun()

            except:
                st.error("ID inválido")

