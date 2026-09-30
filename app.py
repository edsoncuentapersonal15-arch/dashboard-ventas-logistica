import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io

st.set_page_config(
    page_title="Tablero de Control - Ventas vs Logística",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilos CSS estilo Power BI
st.markdown('''
    <style>
        .block-container {
            padding-top: 0.8rem;
            padding-bottom: 0rem;
            padding-left: 1rem;
            padding-right: 1rem;
            max-width: 100%;
        }
        header {visibility: hidden;}
        footer {visibility: hidden;}
        div[data-testid="stMetricValue"] {
            font-size: 1.5rem !important;
            font-weight: bold;
        }
        div[data-testid="stMetricLabel"] {
            font-size: 0.85rem !important;
            font-weight: 600;
        }
        .header-title {
            background-color: #1f2937;
            color: white;
            padding: 8px 15px;
            border-radius: 6px;
            margin-bottom: 10px;
        }
        .header-title h3 {
            margin: 0;
            color: white;
            font-size: 1.2rem;
        }
    </style>
''', unsafe_allow_html=True)

st.markdown('''
    <div class="header-title">
        <h3>📊 TABLERO DE CONTROL: REQUERIDO (CUENTAS CLAVE) VS REGISTRADO (LOGÍSTICA)</h3>
    </div>
''', unsafe_allow_html=True)

# IDs de Google Drive
ID_CUENTAS_CLAVE = "17pMA3Z67ZBvi2c5REZquddGzyVY_gzJI"
ID_LOGISTICA = "1VvjsrpFE__Myp2m9OQt9s_GZtCCkHNbQ"

@st.cache_data(ttl=600)
def descargar_excel_drive(file_id):
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    res = requests.get(url)
    if res.status_code != 200:
        st.error(f"Error al descargar el archivo desde Google Drive (Status Code: {res.status_code}). Verifica los permisos del enlace.")
        st.stop()
    return pd.read_excel(io.BytesIO(res.content), sheet_name=None)

@st.cache_data(ttl=600)
def cargar_y_unir_hojas():
    def procesar_multihojas(dict_hojas):
        dfs = []
        mapeo_detectado = {}

        for nombre_hoja, df in dict_hojas.items():
            if df.empty:
                continue

            df['Canal'] = str(nombre_hoja).strip()

            cols_orig = list(df.columns)
            cols_clean = {c: str(c).strip().lower() for c in cols_orig}

            # 1. FECHA
            col_fecha_nom = None
            for orig, clean in cols_clean.items():
                if any(k in clean for k in ['fecha registro', 'fecha_registro', 'f_registro', 'fecha pedido', 'f.emision', 'fecha emision']):
                    col_fecha_nom = orig
                    break
            if not col_fecha_nom:
                for orig, clean in cols_clean.items():
                    if 'fech' in clean and 'despacho' not in clean and 'entrega' not in clean:
                        col_fecha_nom = orig
                        break
            if not col_fecha_nom:
                col_fecha_nom = cols_orig[0]

            # 2. SOLES
            col_soles_nom = None
            for orig, clean in cols_clean.items():
                if any(k in clean for k in ['total soles', 'total_soles', 'monto soles', 'soles']):
                    col_soles_nom = orig
                    break
            if not col_soles_nom:
                for orig, clean in cols_clean.items():
                    if any(k in clean for k in ['monto', 'importe', 'total', 'venta', 'val_neto']):
                        col_soles_nom = orig
                        break
            if not col_soles_nom:
                num_cols = df.select_dtypes(include=['number']).columns
                col_soles_nom = num_cols[0] if len(num_cols) > 0 else cols_orig[0]

            # 3. UNIDADES: PRIORIDAD ESTRICTA (UNIDADES > CANTIDAD > DOCENAS)
            col_cant_nom = None
            for orig, clean in cols_clean.items():
                if 'unidades' in clean or clean == 'unid' or 'unid.' in clean:
                    col_cant_nom = orig
                    break

            if not col_cant_nom:
                for orig, clean in cols_clean.items():
                    if 'cantidad' in clean or 'cant' in clean:
                        col_cant_nom = orig
                        break

            if not col_cant_nom:
                for orig, clean in cols_clean.items():
                    if 'docena' in clean or 'docenas' in clean:
                        col_cant_nom = orig
                        break

            mapeo_detectado[nombre_hoja] = {
                'Fecha Usada': str(col_fecha_nom),
                'Soles Usado': str(col_soles_nom),
                'Unidades Usada': str(col_cant_nom) if col_cant_nom else "Fijo (1 por fila)"
            }

            df['Fecha'] = pd.to_datetime(df[col_fecha_nom], errors='coerce').fillna(pd.Timestamp.now())
            df['Mes_Num'] = df['Fecha'].dt.month

            meses_map = {1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 5:'Mayo', 6:'Junio',
                         7:'Julio', 8:'Agosto', 9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'}
            df['Mes'] = df['Mes_Num'].map(meses_map)

            if df[col_soles_nom].dtype == object:
                df['Soles'] = pd.to_numeric(df[col_soles_nom].astype(str).str.replace('S/', '', regex=False).str.replace(',', '', regex=False).str.strip(), errors='coerce').fillna(0)
            else:
                df['Soles'] = pd.to_numeric(df[col_soles_nom], errors='coerce').fillna(0)

            if col_cant_nom and col_cant_nom in df.columns:
                df['Unidades'] = pd.to_numeric(df[col_cant_nom], errors='coerce').fillna(1)
            else:
                df['Unidades'] = 1

            dfs.append(df)

        return (pd.concat(dfs, ignore_index=True) if dfs else None), mapeo_detectado

    dict_cuentas = descargar_excel_drive(ID_CUENTAS_CLAVE)
    dict_logistica = descargar_excel_drive(ID_LOGISTICA)

    df_cuentas, map_c = procesar_multihojas(dict_cuentas)
    df_logistica, map_l = procesar_multihojas(dict_logistica)

    return df_cuentas, df_logistica, map_c, map_l

df_cuentas, df_logistica, map_c, map_l = cargar_y_unir_hojas()

# Layout Principal
col_principal, col_lateral = st.columns([3.2, 1])

with col_lateral:
    st.markdown("##### 🎯 Filtros de Selección")

    if st.button("🔄 Actualizar Datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    canales_unicos = sorted(list(set(df_cuentas['Canal'].unique()).union(set(df_logistica['Canal'].unique()))))
    opcion_canal = st.selectbox("Canal (Hoja):", options=["Todos"] + canales_unicos, key="sel_canal")

    orden_meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    meses_presentes = [m for m in orden_meses if m in df_cuentas['Mes'].unique()]
    opcion_mes = st.selectbox("Mes:", options=["Todos"] + meses_presentes, key="sel_mes")

    # SECCIÓN DE DIAGNÓSTICO
    with st.expander("🔍 Verificar Columnas Detectadas"):
        st.caption("**BD Cuentas Clave:**")
        st.json(map_c)
        st.caption("**BD Logística:**")
        st.json(map_l)

# Filtrado
df_c_filt = df_cuentas.copy()
df_l_filt = df_logistica.copy()

if opcion_canal != "Todos":
    df_c_filt = df_c_filt[df_c_filt['Canal'] == opcion_canal]
    df_l_filt = df_l_filt[df_l_filt['Canal'] == opcion_canal]

if opcion_mes != "Todos":
    df_c_filt = df_c_filt[df_c_filt['Mes'] == opcion_mes]
    df_l_filt = df_l_filt[df_l_filt['Mes'] == opcion_mes]

# Totales
unid_req = df_c_filt['Unidades'].sum()
unid_reg = df_l_filt['Unidades'].sum()
dif_unid = unid_reg - unid_req

soles_req = df_c_filt['Soles'].sum()
soles_reg = df_l_filt['Soles'].sum()
dif_soles = soles_reg - soles_req

with col_principal:
    # Indicadores Numéricos
    u1, u2, u3 = st.columns(3)
    u1.metric("📦 Unid. Requeridas (Cuentas)", f"{unid_req:,.0f}")
    u2.metric("📋 Unid. Registradas (Logística)", f"{unid_reg:,.0f}")
    u3.metric("⚖️ Dif. Unidades", f"{dif_unid:,.0f}", delta_color="normal" if dif_unid >= 0 else "inverse")

    s1, s2, s3 = st.columns(3)
    s1.metric("💵 Soles Requeridos (Cuentas)", f"S/ {soles_req:,.2f}")
    s2.metric("💳 Soles Registrados (Logística)", f"S/ {soles_reg:,.2f}")
    s3.metric("⚖️ Dif. Soles", f"S/ {dif_soles:,.2f}", delta_color="normal" if dif_soles >= 0 else "inverse")

    st.markdown("<hr style='margin: 6px 0;'>", unsafe_allow_html=True)

    # 4 Gráficos de Columnas
    gc1, gc2 = st.columns(2)

    df_c_mes = df_c_filt.groupby(['Mes_Num', 'Mes'])[['Unidades', 'Soles']].sum().reset_index().sort_values('Mes_Num')
    df_l_mes = df_l_filt.groupby(['Mes_Num', 'Mes'])[['Unidades', 'Soles']].sum().reset_index().sort_values('Mes_Num')

    with gc1:
        fig_u_req = px.bar(df_c_mes, x='Mes', y='Unidades', text_auto='.2s', title="📦 Unidades Requeridas por Mes")
        fig_u_req.update_layout(height=220, margin=dict(l=10, r=10, t=30, b=10), template="plotly_white")
        fig_u_req.update_traces(marker_color='#2980b9')
        st.plotly_chart(fig_u_req, use_container_width=True)

        fig_s_req = px.bar(df_c_mes, x='Mes', y='Soles', text_auto='.2s', title="💵 Soles Requeridos por Mes")
        fig_s_req.update_layout(height=220, margin=dict(l=10, r=10, t=30, b=10), template="plotly_white")
        fig_s_req.update_traces(marker_color='#27ae60')
        st.plotly_chart(fig_s_req, use_container_width=True)

    with gc2:
        fig_u_reg = px.bar(df_l_mes, x='Mes', y='Unidades', text_auto='.2s', title="📋 Unidades Registradas por Mes")
        fig_u_reg.update_layout(height=220, margin=dict(l=10, r=10, t=30, b=10), template="plotly_white")
        fig_u_reg.update_traces(marker_color='#e74c3c')
        st.plotly_chart(fig_u_reg, use_container_width=True)

        fig_s_reg = px.bar(df_l_mes, x='Mes', y='Soles', text_auto='.2s', title="💳 Soles Registrados por Mes")
        fig_s_reg.update_layout(height=220, margin=dict(l=10, r=10, t=30, b=10), template="plotly_white")
        fig_s_reg.update_traces(marker_color='#8e44ad')
        st.plotly_chart(fig_s_reg, use_container_width=True)

with col_lateral:
    st.markdown("<hr style='margin: 8px 0;'>", unsafe_allow_html=True)

    # Pasteles
    df_pie_unid = pd.DataFrame({
        'Origen': ['Requerido', 'Registrado'],
        'Unidades': [unid_req, unid_reg]
    })
    fig_pie_u = px.pie(df_pie_unid, names='Origen', values='Unidades', hole=0.4, title="📦 Total Unidades")
    fig_pie_u.update_layout(height=220, margin=dict(l=5, r=5, t=30, b=5), showlegend=False)
    fig_pie_u.update_traces(textposition='inside', textinfo='percent+label', marker=dict(colors=['#2980b9', '#e74c3c']))
    st.plotly_chart(fig_pie_u, use_container_width=True)

    df_pie_soles = pd.DataFrame({
        'Origen': ['Requerido', 'Registrado'],
        'Soles': [soles_req, soles_reg]
    })
    fig_pie_s = px.pie(df_pie_soles, names='Origen', values='Soles', hole=0.4, title="💰 Total Soles")
    fig_pie_s.update_layout(height=220, margin=dict(l=5, r=5, t=30, b=5), showlegend=False)
    fig_pie_s.update_traces(textposition='inside', textinfo='percent+label', marker=dict(colors=['#27ae60', '#8e44ad']))
    st.plotly_chart(fig_pie_s, use_container_width=True)
