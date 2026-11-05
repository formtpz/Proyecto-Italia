import streamlit as st
import pandas as pd
from db import leer_dataframe, transaccion
from permisos import validar_acceso

def render():
    # =========================
    # Control de acceso
    # =========================
    validar_acceso("Historial")

    usuario = st.session_state.get("usuario")

    perfil = usuario["perfil"]        # 1 = Admin / Coordinador
                                      # 3 = Operativo / Supervisor
    puesto = usuario["puesto"].lower()
    cedula_usuario = usuario["cedula"]
    nombre_usuario = usuario["nombre"]

    if perfil not in (1, 3, 4, 5):
        st.error("No tiene permiso para acceder al historial")
        st.stop()

    st.title("📈 Historial de Reportes")


    # =========================
    # Filtro de fechas
    # =========================
    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio = st.date_input("Desde")
    with col2:
        fecha_fin = st.date_input("Hasta")

    # =========================
    # Selector de alcance según perfil
    # =========================
    where_extra = ""
    params_base = [fecha_inicio, fecha_fin]

    # -------- OPERADOR --------
    if perfil == 3 or perfil == 4 and puesto == "operario catastral":
        where_extra = " AND r.cedula_personal = %s"
        params_base.append(cedula_usuario)

    # -------- SUPERVISOR --------
    elif perfil == 3:
        opcion = st.radio(
            "Ver reportes de:",
            ["Propios", "Operadores a cargo"],
            horizontal=True
        )

        if opcion == "Propios":
            where_extra = " AND r.cedula_personal = %s"
            params_base.append(cedula_usuario)
        else:
            where_extra = " AND r.supervisor_nombre = %s"
            params_base.append(nombre_usuario)

    # -------- ADMIN / COORDINADOR --------
    elif perfil == 1:
        opcion = st.radio(
            "Ver reportes:",
            ["Totales", "Propios"],
            horizontal=True
        )

        if opcion == "Propios":
            where_extra = " AND r.cedula_personal = %s"
            params_base.append(cedula_usuario)
        else:
            where_extra = ""

    # =========================
    # REPORTES DE PRODUCCIÓN
    # =========================
    st.subheader("📊 Reportes de Producción")

    query_prod = f"""
    SELECT 
        r.id,
        r.fecha_reporte,
        p.nombre_completo AS persona,
        r.supervisor_nombre AS supervisor,
        r.horas,
        r.produccion,
        r.aprobados,
        r.rechazados,
        r.observaciones
    FROM reportes r
    JOIN personal p ON p.cedula = r.cedula_personal
    WHERE r.tipo_reporte = 'produccion'
      AND r.fecha_reporte BETWEEN %s AND %s
      {where_extra}
    ORDER BY r.fecha_reporte, persona
    """

    df_prod = leer_dataframe(query_prod, params=params_base)
    st.dataframe(df_prod, use_container_width=True, hide_index=True)

    # =========================
    # REPORTES DE EVENTOS
    # =========================
    st.subheader("🗂️ Reportes de Eventos")

    query_eventos = f"""
    SELECT 
        r.id,
        r.fecha_reporte,
        p.nombre_completo AS persona,
        r.supervisor_nombre AS supervisor,
        r.horas,
        te.nombre AS tipo_evento,
        r.observaciones
    FROM reportes r
    JOIN personal p ON p.cedula = r.cedula_personal
    LEFT JOIN tipos_evento te ON te.id = r.tipo_evento_id
    WHERE r.tipo_reporte = 'evento'
      AND r.fecha_reporte BETWEEN %s AND %s
      {where_extra}
    ORDER BY r.fecha_reporte, persona
    """

    df_eventos = leer_dataframe(query_eventos, params=params_base)
    st.dataframe(df_eventos, use_container_width=True, hide_index=True)

    # =========================
    # RESUMEN DIARIO DE HORAS (POR PERSONA)
    # =========================
    st.subheader("⏱️ Resumen Diario de Horas por Persona")

    query_horas = f"""
    SELECT 
        r.fecha_reporte,
        p.nombre_completo AS persona,
        SUM(r.horas) AS total_horas
    FROM reportes r
    JOIN personal p ON p.cedula = r.cedula_personal
    WHERE r.fecha_reporte BETWEEN %s AND %s
      {where_extra}
    GROUP BY r.fecha_reporte, p.nombre_completo
    ORDER BY r.fecha_reporte, persona
    """

    df_horas = leer_dataframe(query_horas, params=params_base)

    df_horas["estado"] = df_horas["total_horas"].apply(
        lambda x: "✅ OK" if 8.4 <= float(x) <= 8.6 else "⚠️ Revisar"
    )

    st.dataframe(df_horas, use_container_width=True)
