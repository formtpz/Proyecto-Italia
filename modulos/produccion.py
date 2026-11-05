import streamlit as st
from datetime import date
from db import consultar_uno, transaccion
from permisos import validar_acceso

def render():
    validar_acceso("Reportes Producción")
    usuario = st.session_state["usuario"]
    if usuario["perfil"] not in (1, 3, 4, 5):
        st.error("No tiene permiso para acceder a Producción")
        st.stop()

    st.title("📊 Reporte de Producción")
    proceso = consultar_uno("SELECT id FROM procesos WHERE id = 1")
    if not proceso:
        st.error("No existe el proceso 1 (Producción) en el esquema italia.")
        return

    with st.form("form_reporte_produccion"):
        fecha_reporte = st.date_input("Fecha", value=date.today())
        horas = st.number_input("Horas laboradas (decimal)", min_value=0.0,
                                max_value=24.0, step=0.5)
        tipo_produccion = st.text_input(
            "Tipo de producción / trabajo atendido", max_chars=200,
            help="Describa qué trabajo de producción realizó.")
        produccion = st.number_input("Cantidad producida", min_value=0, step=1)
        estado = st.selectbox("Estado", [ "finalizado","pendiente", "corrección"])
        observaciones = st.text_area("Observaciones")
        submit = st.form_submit_button("Guardar reporte")

    if submit:
        try:
            with transaccion() as cur:
                cur.execute("SELECT supervisor FROM personal WHERE cedula = %s",
                            (usuario["cedula"],))
                fila = cur.fetchone()
                supervisor = fila[0] if fila else None
                cur.execute("""
                    INSERT INTO reportes (
                        tipo_reporte, cedula_personal, cedula_quien_reporta,
                        supervisor_nombre, fecha_reporte, semana, año, horas,
                        proceso_id, tipo_produccion, produccion, estado,
                        observaciones, perfil, puesto
                    ) VALUES (
                        'produccion', %s, %s, %s, %s, %s, %s, %s,
                        1, %s, %s, %s, %s, %s, %s
                    )
                """, (usuario["cedula"], usuario["cedula"], supervisor,
                      fecha_reporte, fecha_reporte.isocalendar()[1],
                      fecha_reporte.year, horas, tipo_produccion.strip() or None,
                      produccion, estado, observaciones or None,
                      usuario["perfil"], usuario["puesto"]))
            st.success("✅ Reporte guardado correctamente")
        except Exception as exc:
            st.error("❌ Error al guardar el reporte")
            st.exception(exc)
