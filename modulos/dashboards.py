import streamlit as st
import pandas as pd
from db import leer_dataframe
from permisos import validar_acceso

def render():
    validar_acceso("Dashboards")
    usuario = st.session_state["usuario"]
    if usuario["perfil"] not in (1, 5):
        st.error("Acceso restringido")
        st.stop()
    st.title("📊 Dashboards")
    st.subheader("👥 Personal activo")
    df = leer_dataframe("""
        SELECT puesto, COUNT(*) AS cantidad
        FROM personal WHERE estado = 'activo'
        GROUP BY puesto ORDER BY puesto
    """)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.divider()
    st.subheader("📅 Resumen de reportes")
    c1, c2 = st.columns(2)
    with c1:
        inicio = st.date_input("Desde", key="dash_desde")
    with c2:
        fin = st.date_input("Hasta", key="dash_hasta")
    if inicio > fin:
        st.warning("La fecha inicial no puede ser posterior a la final")
        return
    resumen = leer_dataframe("""
        SELECT tipo_reporte, COUNT(*) AS reportes,
               COALESCE(SUM(horas), 0) AS horas,
               COALESCE(SUM(produccion), 0) AS produccion
        FROM reportes
        WHERE fecha_reporte BETWEEN %s AND %s
        GROUP BY tipo_reporte ORDER BY tipo_reporte
    """, (inicio, fin))
    st.dataframe(resumen, use_container_width=True, hide_index=True)
