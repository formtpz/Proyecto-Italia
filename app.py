import streamlit as st
from permisos import PERMISOS_POR_PERFIL

# =========================
# CONFIGURACIÓN GENERAL (SIEMPRE PRIMERO)
# =========================
st.set_page_config(
    page_title="Sistema de Reportes",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"  # evita quedar atrapado
)

# =========================
# USUARIO EN SESIÓN (SI EXISTE)
# =========================
usuario = st.session_state.get("usuario")

# =========================
# ESTILOS GLOBALES SEGUROS
# =========================
st.markdown("""
<style>

/* 1. Ocultar menú ⋮ */
#MainMenu {
    visibility: hidden;
}

/* 2. Ocultar footer */
footer {
    visibility: hidden;
}

/* 3. Ocultar SOLO los iconos (Share, Star, Edit, GitHub) */
div[data-testid="stToolbarActions"] {
    display: none !important;
}

/* 4. Mantener toolbar vivo (NO tocar visibilidad) */
div[data-testid="stToolbar"] {
    min-height: 2rem;
}

/* 5. Opcional: eliminar decoración superior extra */
div[data-testid="stDecoration"] {
    display: none;
}

</style>
""", unsafe_allow_html=True)


# =========================
# USUARIO NO LOGUEADO → LOGIN
# =========================
if not usuario:
    from modulos.login import render
    render()
    st.stop()

# =========================
# USUARIO LOGUEADO → MENÚ DINÁMICO
# =========================
perfil = usuario["perfil"]
opciones = PERMISOS_POR_PERFIL.get(perfil, [])

with st.sidebar:
    st.image("logo.png", width=1200)
    st.markdown("### Menú")
    opcion = st.radio("Seleccione una opción", opciones)

# =========================
# ROUTER DE MÓDULOS
# =========================
if opcion == "Dashboards":
    from modulos.dashboards import render
    render()

elif opcion == "Reportes Producción":
    from modulos.produccion import render
    render()

elif opcion == "RRHH":
    from modulos.rrhh import render
    render()

elif opcion == "Eventos":
    from modulos.eventos import render
    render()

elif opcion == "Historial":
    from modulos.historial import render
    render()

elif opcion == "Correcciones":
    from modulos.correcciones import render
    render()

elif opcion == "Cerrar Sesion":
    from modulos.cerrar_sesion import render
    render()

