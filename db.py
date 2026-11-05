"""Acceso serializado a PostgreSQL: una conexión por proceso Streamlit."""
import threading
from contextlib import contextmanager
import psycopg2
import pandas as pd
import streamlit as st

@st.cache_resource
def _resource():
    return {"conn": psycopg2.connect(st.secrets["db_credentials"]["URI"]),
            "lock": threading.RLock()}

@contextmanager
def transaccion():
    recurso = _resource()
    with recurso["lock"]:
        conn = recurso["conn"]
        if conn.closed:
            conn = psycopg2.connect(st.secrets["db_credentials"]["URI"])
            recurso["conn"] = conn
        try:
            with conn.cursor() as cur:
                yield cur
            conn.commit()
        except BaseException:
            conn.rollback()
            raise

def consultar(sql, params=None):
    with transaccion() as cur:
        cur.execute(sql, params)
        return cur.fetchall()

def consultar_uno(sql, params=None):
    with transaccion() as cur:
        cur.execute(sql, params)
        return cur.fetchone()

def leer_dataframe(sql, params=None):
    with transaccion() as cur:
        cur.execute(sql, params)
        columnas = [d[0] for d in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=columnas)
