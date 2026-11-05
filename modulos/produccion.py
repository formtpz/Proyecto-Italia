import streamlit as st
from datetime import date
from db import consultar, consultar_uno, transaccion
from permisos import validar_acceso

def render():
    validar_acceso("Reportes Producción")
    usuario = st.session_state["usuario"]
    if usuario["perfil"] not in (1, 3, 4, 5):
        st.error("No tiene permiso para acceder a Producción")
        st.stop()
    st.title("📊 Reporte de Producción")
    procesos = consultar("SELECT id, nombre FROM procesos WHERE id <> 0 ORDER BY id")
    if not procesos:
        st.warning("No existen procesos registrados")
        return
    procesos_dict = {nombre: pid for pid, nombre in procesos}
    with st.form("form_reporte_produccion"):
        proceso_nombre = st.selectbox("Proceso", list(procesos_dict))
        proceso_id = procesos_dict[proceso_nombre]
        es_control_calidad = proceso_id == 2
        es_omisiones = proceso_id == 3
        fecha_reporte = st.date_input("Fecha", value=date.today())
        horas = st.number_input(
            "Horas laboradas en formato decimal (40 min = 0.67 h; jornada diaria 8.5 h)",
            min_value=0.0, max_value=12.5, step=0.5)
        if es_control_calidad:
            aprobados = st.number_input("Aprobados", min_value=0)
            rechazados = st.number_input("Rechazados", min_value=0)
            produccion = None
            estados = ["pendiente", "aprobado", "rechazado"]
        else:
            produccion = st.number_input("Producción", min_value=0)
            aprobados = None
            rechazados = None
            estados = ["finalizado", "pendiente"] if es_omisiones else ["pendiente", "finalizado", "corregido"]
        estado = st.selectbox("Estado", estados)
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
                        proceso_id, produccion, aprobados, rechazados, estado,
                        observaciones, perfil, puesto
                    ) VALUES (
                        'produccion', %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (usuario["cedula"], usuario["cedula"], supervisor,
                      fecha_reporte, fecha_reporte.isocalendar()[1],
                      fecha_reporte.year, horas, proceso_id, produccion,
                      aprobados, rechazados, estado, observaciones or None,
                      usuario["perfil"], usuario["puesto"]))
            st.success("✅ Reporte guardado correctamente")
        except Exception as exc:
            st.error("❌ Error al guardar el reporte")
            st.exception(exc)
