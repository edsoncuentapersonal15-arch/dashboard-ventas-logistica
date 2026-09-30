import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io

# ---------------------------------------------------------
# 1. IDS DE TUS ARCHIVOS DE GOOGLE DRIVE (YA CONFIGURADOS)
# ---------------------------------------------------------
ID_CUENTAS_CLAVE = "17pMA3Z67ZBvi2c5REZquddGzyVY_gzJI"
ID_LOGISTICA = "1VvjsrpFE__Myp2m9OQt9s_GZtCCkHNbQ"

st.set_page_config(
    page_title="Dashboard Ejecutivo | Ventas & Logística",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .metric-card {
        background-color: #f8f9fa;
        border-left: 5px solid #0d6efd;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .metric-title { font-size: 14px; color: #6c757d; font-weight: 600; text-transform: uppercase; }
    .metric-value { font-size: 24px; color: #212529; font-weight: bold; margin-top: 5px; }
    </style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)  # Revisa cambios en Drive cada 5 minutos
def cargar_desde_drive_url(file_id):
    if not file_id:
        return None, {}
    
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    response = requests.get(url)
    if response.status_code != 200:
        return None, {}
    
    try:
        dict_hojas = pd.read_excel(io.BytesIO(response.content), sheet_name=None)
    except Exception:
        return None, {}

    dfs = []
    mapeo_detectado = {}

    for nombre_hoja, df in dict_hojas.items():
        if df.empty:
            continue

        df['Canal'] = str(nombre_hoja).strip()
        cols_orig = list(df.columns)
        cols_clean = {c: str(c).strip().lower() for c in cols_orig}

        # 1. Detectar Fecha
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

        # 2. Detectar Soles
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

        # 3. Detectar Unidades
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

# --- CARGA DE DATOS ---
with st.spinner("Conectando con Google Drive y procesando datos..."):
    df_cuentas, map_c = cargar_desde_drive_url(ID_CUENTAS_CLAVE)
    df_logistica, map_l = cargar_desde_drive_url(ID_LOGISTICA)

# --- NAVEGACIÓN PRINCIPAL ---
st.sidebar.title("📌 Navegación Principal")
pagina = st.sidebar.radio("Seleccione Módulo:", ["💼 Cuentas Clave", "🚚 Logística Comercial", "⚙️ Diagnóstico Mapeo"])

if st.sidebar.button("🔄 Forzar Actualización Datos"):
    st.cache_data.clear()
    st.rerun()

# --- MÓDULO 1: CUENTAS CLAVE ---
if pagina == "💼 Cuentas Clave":
    st.title("💼 Dashboard de Cuentas Clave")
    
    if df_cuentas is not None and not df_cuentas.empty:
        st.sidebar.subheader("🎯 Filtros Cuentas Clave")
        canales_c = st.sidebar.multiselect("Canal / Hoja", options=df_cuentas['Canal'].unique(), default=df_cuentas['Canal'].unique())
        meses_c = st.sidebar.multiselect("Mes", options=df_cuentas['Mes'].unique(), default=df_cuentas['Mes'].unique())
        
        df_c_filtered = df_cuentas[(df_cuentas['Canal'].isin(canales_c)) & (df_cuentas['Mes'].isin(meses_c))]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="metric-card"><div class="metric-title">Ventas Totales</div><div class="metric-value">S/ {df_c_filtered["Soles"].sum():,.2f}</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric-card"><div class="metric-title">Unidades Vendidas</div><div class="metric-value">{df_c_filtered["Unidades"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="metric-card"><div class="metric-title">Total Pedidos / Filas</div><div class="metric-value">{len(df_c_filtered):,}</div></div>', unsafe_allow_html=True)
        
        st.markdown("---")
        c_left, c_right = st.columns(2)
        with c_left:
            fig_canal = px.bar(df_c_filtered.groupby('Canal')['Soles'].sum().reset_index(), x='Canal', y='Soles', title="Ventas por Canal (S/)", text_auto='.2s', color='Canal')
            st.plotly_chart(fig_canal, use_container_width=True)
        with c_right:
            df_mes = df_c_filtered.groupby(['Mes_Num', 'Mes'])['Soles'].sum().reset_index().sort_values('Mes_Num')
            fig_mes = px.line(df_mes, x='Mes', y='Soles', title="Tendencia de Ventas por Mes", markers=True)
            st.plotly_chart(fig_mes, use_container_width=True)
    else:
        st.warning("⚠️ No se pudieron cargar los datos de Cuentas Clave. Revisa los permisos de acceso en Google Drive.")

# --- MÓDULO 2: LOGÍSTICA ---
elif pagina == "🚚 Logística Comercial":
    st.title("🚚 Dashboard de Logística Comercial")
    
    if df_logistica is not None and not df_logistica.empty:
        st.sidebar.subheader("🎯 Filtros Logística")
        canales_l = st.sidebar.multiselect("Canal / Hoja", options=df_logistica['Canal'].unique(), default=df_logistica['Canal'].unique())
        meses_l = st.sidebar.multiselect("Mes", options=df_logistica['Mes'].unique(), default=df_logistica['Mes'].unique())
        
        df_l_filtered = df_logistica[(df_logistica['Canal'].isin(canales_l)) & (df_logistica['Mes'].isin(meses_l))]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="metric-card"><div class="metric-title">Facturación Total</div><div class="metric-value">S/ {df_l_filtered["Soles"].sum():,.2f}</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric-card"><div class="metric-title">Volumen Despachado</div><div class="metric-value">{df_l_filtered["Unidades"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="metric-card"><div class="metric-title">Registros Logísticos</div><div class="metric-value">{len(df_l_filtered):,}</div></div>', unsafe_allow_html=True)
            
        st.markdown("---")
        l_left, l_right = st.columns(2)
        with l_left:
            fig_l_canal = px.pie(df_l_filtered.groupby('Canal')['Soles'].sum().reset_index(), values='Soles', names='Canal', title="Distribución de Facturación por Canal")
            st.plotly_chart(fig_l_canal, use_container_width=True)
        with l_right:
            fig_l_unid = px.bar(df_l_filtered.groupby('Canal')['Unidades'].sum().reset_index(), x='Canal', y='Unidades', title="Unidades Despachadas por Canal", text_auto='.2s')
            st.plotly_chart(fig_l_unid, use_container_width=True)
    else:
        st.warning("⚠️ No se pudieron cargar los datos de Logística. Revisa los permisos de acceso en Google Drive.")

# --- MÓDULO 3: DIAGNÓSTICO ---
elif pagina == "⚙️ Diagnóstico Mapeo":
    st.title("⚙️ Diagnóstico Mapeo Automático de Columnas")
    st.info("Revisa aquí qué columna detectó automáticamente el sistema para cada pestaña de tu Excel.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("💼 Hojas Cuentas Clave")
        st.json(map_c)
    with col_b:
        st.subheader("🚚 Hojas Logística")
        st.json(map_l)
