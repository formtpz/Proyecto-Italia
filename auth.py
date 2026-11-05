import streamlit as st
from db import consultar_uno

def login_usuario(cedula, password):

    user = consultar_uno("""
        SELECT cedula, nombre_completo, perfil, puesto
        FROM personal
        WHERE cedula = %s
          AND contraseña = %s
          AND estado = 'activo'
    """, (cedula.strip(), password.strip()))


    if user:
        st.session_state["usuario"] = {
            "cedula": user[0],
            "nombre": user[1],
            "perfil": user[2],
            "puesto": user[3]
        }
        st.rerun()
    
    else:
        st.error("Credenciales incorrectas")
