import streamlit as st
from permisos import validar_acceso

def render():
    # =========================
    # Control de acceso
    # =========================
    validar_acceso("Cerrar Sesion")

    st.title("🚪 Cerrar sesión")

    st.info("Su sesión será cerrada de forma segura.")

    if st.button("Confirmar cierre de sesión"):
        # =========================
        # Limpiar sesión
        # =========================
        st.session_state.clear()

        st.success("✅ Sesión cerrada correctamente")
        st.info("Volviendo al login...")

        # Fuerza recarga para volver a app.py → login
        st.rerun()
