import streamlit as st
from datetime import date
from db import consultar, transaccion
from permisos import validar_acceso

def render():
    # =========================
    # Control de acceso
    # =========================
    validar_acceso("Eventos")

    usuario = st.session_state.get("usuario")

    perfil = usuario["perfil"]
    puesto = (usuario["puesto"] or "").strip().casefold()
    es_operario = perfil == 3 or (perfil == 4 and puesto == "operario catastral")
    cedula_reporta = usuario["cedula"]
    nombre_usuario = usuario["nombre"]

    # Seguridad extra
    if perfil not in (1, 3, 4, 5):
        st.error("No tiene permiso para acceder a Reportes de Eventos")
        st.stop()

    st.title("📌 Reporte de Eventos")


    # =========================
    # Cargar tipos de evento
    # =========================
    tipos_evento = consultar("""
        SELECT id, nombre
        FROM tipos_evento
        ORDER BY nombre
    """)

    if not tipos_evento:
        st.error("No existen tipos de evento registrados")
        st.stop()

    # =========================
    # Restricción Operador Catastral
    # =========================
    if es_operario:
        tipos_evento = [
            (id_, nombre)
            for id_, nombre in tipos_evento
            if id_ in (3, 16)
        ]

    if not tipos_evento:
        st.error("No existen tipos de evento disponibles para su perfil")
        st.stop()

    tipos_evento_dict = {nombre: id_ for id_, nombre in tipos_evento}

    # =========================
    # Cargar personal según jerarquía
    # =========================
    if es_operario:
        # El operario SOLO se reporta a sí mismo
        resultado_personal = consultar("""
            SELECT cedula, nombre_completo, perfil, puesto, supervisor
            FROM personal
            WHERE cedula = %s
              AND estado = 'activo'
        """, (cedula_reporta,))
    else:
        if puesto == "coordinador" or puesto == "supervisor" or puesto in ("tecnico sig", "técnico sig"):
            resultado_personal = consultar("""
                SELECT cedula, nombre_completo, perfil, puesto, supervisor
                FROM personal
                WHERE estado = 'activo'
                ORDER BY nombre_completo
            """)
        else:
            resultado_personal = consultar("""
                SELECT cedula, nombre_completo, perfil, puesto, supervisor
                FROM personal
                WHERE estado = 'activo'
                  AND (supervisor = %s OR cedula = %s)
                ORDER BY nombre_completo
            """, (nombre_usuario, cedula_reporta))

    personal = resultado_personal

    if not personal:
        st.error("No existe personal disponible para reportar")
        st.stop()

    personal_dict = {
        f"{nombre} ({ced})": {
            "cedula": ced,
            "perfil": perfil_p,
            "puesto": puesto_p,
            "supervisor": supervisor_p
        }
        for ced, nombre, perfil_p, puesto_p, supervisor_p in personal
    }

    # =========================
    # Formulario
    # =========================
    with st.form("form_reporte_evento"):
        fecha_reporte = st.date_input(
            "Fecha del evento",
            value=date.today()
        )

        tipo_evento_nombre = st.selectbox(
            "Tipo de evento",
            options=list(tipos_evento_dict.keys())
        )

        horas = st.number_input(
            "Horas",
            min_value=0.0,
            max_value=24.0,
            step=0.5
        )

        # =========================
        # Selección de personal
        # =========================
        if es_operario:
            personal_seleccionado = list(personal_dict.keys())
            st.info("Como Operario Catastral, solo puede reportarse a sí mismo.")
        else:
            personal_seleccionado = st.multiselect(
                "Personal al que aplica el evento",
                options=list(personal_dict.keys())
            )

        observaciones = st.text_area(
            "Observaciones (opcional)",
            value=""
        )

        submit = st.form_submit_button("Guardar evento")

    # =========================
    # Guardar eventos
    # =========================
    if submit:
        if not personal_seleccionado:
            st.warning("Debe seleccionar al menos una persona")
            st.stop()

        semana = fecha_reporte.isocalendar()[1]
        año = fecha_reporte.year
        tipo_evento_id = tipos_evento_dict[tipo_evento_nombre]

        try:
            with transaccion() as cur:
                for persona in personal_seleccionado:
                    datos = personal_dict[persona]
                    cur.execute("SELECT supervisor FROM personal WHERE cedula = %s",
                                (datos["cedula"],))
                    fila = cur.fetchone()
                    supervisor = fila[0] if fila else None
                    cur.execute("""
                        INSERT INTO reportes (
                            tipo_reporte, cedula_personal, cedula_quien_reporta,
                            supervisor_nombre, fecha_reporte, semana, año, horas,
                            tipo_evento_id, observaciones, perfil, puesto
                        ) VALUES ('evento', %s, %s, %s, %s, %s, %s, %s,
                                  %s, %s, %s, %s)
                    """, (datos["cedula"], cedula_reporta, supervisor,
                          fecha_reporte, semana, año, horas, tipo_evento_id,
                          observaciones or None, datos["perfil"], datos["puesto"]))
            st.success("✅ Evento(s) registrado(s) correctamente")
        except Exception as exc:
            st.error("❌ Error al guardar el evento")
            st.exception(exc)
