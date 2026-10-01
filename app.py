import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import calendar
import requests
import io

st.set_page_config(
    page_title="Ventas y Metas Comercial",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# ESTILOS CSS ULTRA-COMPACTOS (FIT TO SCREEN)
# -----------------------------------------------------------------------------
st.markdown('''
    <style>
        /* Reducir márgenes globales al mínimo */
        .block-container {
            padding-top: 0.3rem !important;
            padding-bottom: 0rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 100% !important;
        }
        
        /* Ocultar espacios innecesarios de Streamlit */
        header[data-testid="stHeader"] {display: none;}
        footer {display: none;}
        #MainMenu {visibility: hidden;}
        
        /* Recuadro de Título Encajado */
        .header-title {
            background-color: #1f2937;
            color: white;
            padding: 6px 12px;
            border-radius: 6px;
            margin-bottom: 8px;
            text-align: center;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .header-title h4 {
            margin: 0;
            color: #ffffff;
            font-size: 1.1rem;
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        
        /* Ajuste de Métricas KPI Compactas */
        div[data-testid="stMetricValue"] {
            font-size: 1.25rem !important;
            font-weight: bold;
            line-height: 1.2;
        }
        div[data-testid="stMetricLabel"] {
            font-size: 0.75rem !important;
            font-weight: 600;
            margin-bottom: -2px;
        }
        
        /* Ajustar barra de progreso */
        .stProgress > div > div > div > div {
            height: 6px !important;
        }
        
        /* Ajustar separadores hr */
        hr {
            margin: 0.4rem 0 !important;
        }
    </style>
''', unsafe_allow_html=True)

# Encabezado con ajuste perfecto
st.markdown('''
    <div class="header-title">
        <h4>📊 CENTRO DE CONTROL COMERCIAL & METAS MENSUALES</h4>
    </div>
''', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# CONFIGURACIÓN Y CARGA DINÁMICA DE DATOS DESDE GOOGLE DRIVE
# -----------------------------------------------------------------------------
ID_EXCEL_VENTAS = "17pMA3Z67ZBvi2c5REZquddGzyVY_gzJI"
URL_EXCEL_VENTAS = f"https://docs.google.com/spreadsheets/d/{ID_EXCEL_VENTAS}/export?format=xlsx"

@st.cache_data(ttl=300)
def cargar_datos_ventas_dinamico(url):
    try:
        res = requests.get(url)
        if res.status_code != 200:
            st.error(f"Error al acceder al archivo de Google Drive (Status Code: {res.status_code}).")
            return pd.DataFrame()
        
        hojas_dict = pd.read_excel(io.BytesIO(res.content), sheet_name=None)
        hojas_a_ignorar = ["PARAMETROS", "PLANTILLA", "RESUMEN", "METAS"]
        dfs_consolidados = []
        
        for nombre_hoja, df in hojas_dict.items():
            if nombre_hoja.strip().upper() in hojas_a_ignorar or df.empty:
                continue
            
            df.columns = [str(col).strip() for col in df.columns]
            cols_clean = {c: str(c).strip().lower() for c in df.columns}
            df["CANAL_ORIGEN"] = nombre_hoja.strip()
            
            col_fecha = next((orig for orig, clean in cols_clean.items() if any(k in clean for k in ['fecha registro', 'fecha_registro', 'fecha', 'f_registro'])), None)
            col_cliente = next((orig for orig, clean in cols_clean.items() if any(k in clean for k in ['cliente', 'razon social', 'razon'])), None)
            col_producto = next((orig for orig, clean in cols_clean.items() if any(k in clean for k in ['producto', 'descripcion', 'cod prod'])), None)
            col_cantidad = next((orig for orig, clean in cols_clean.items() if any(k in clean for k in ['unidades', 'cantidad', 'cant', 'docenas'])), None)
            col_monto = next((orig for orig, clean in cols_clean.items() if any(k in clean for k in ['total soles', 'soles', 'monto', 'total'])), None)
            
            if col_fecha and col_monto:
                df_temp = pd.DataFrame()
                df_temp["FECHA"] = pd.to_datetime(df[col_fecha], errors='coerce')
                df_temp["CANAL"] = df["CANAL_ORIGEN"]
                df_temp["CLIENTE"] = df[col_cliente].astype(str) if col_cliente else "Cliente No Especificado"
                df_temp["PRODUCTO"] = df[col_producto].astype(str) if col_producto else "General"
                
                if col_cantidad:
                    df_temp["CANTIDAD"] = pd.to_numeric(df[col_cantidad], errors='coerce').fillna(1)
                else:
                    df_temp["CANTIDAD"] = 1
                
                if df[col_monto].dtype == object:
                    df_temp["MONTO_SOLES"] = pd.to_numeric(df[col_monto].astype(str).str.replace('S/', '', regex=False).str.replace(',', '', regex=False).str.strip(), errors='coerce').fillna(0)
                else:
                    df_temp["MONTO_SOLES"] = pd.to_numeric(df[col_monto], errors='coerce').fillna(0)
                
                df_temp = df_temp.dropna(subset=["FECHA"])
                dfs_consolidados.append(df_temp)
                
        if dfs_consolidados:
            df_final = pd.concat(dfs_consolidados, ignore_index=True)
            df_final["AÑO"] = df_final["FECHA"].dt.year
            df_final["MES_NUM"] = df_final["FECHA"].dt.month
            df_final["MES_NOMBRE"] = df_final["FECHA"].dt.strftime("%B")
            df_final["DIA"] = df_final["FECHA"].dt.day
            return df_final
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Error procesando el archivo de Google Drive: {e}")
        return pd.DataFrame()

# Carga de datos
df_ventas = cargar_datos_ventas_dinamico(URL_EXCEL_VENTAS)

# -----------------------------------------------------------------------------
# SIDEBAR: FILTROS DESPLEGABLES Y CONFIGURACIÓN
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Configuración & Filtros")
    
    if st.button("🔄 Actualizar Datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    st.markdown("---")
    st.subheader("🎯 Meta Comercial del Mes")
    meta_mensual = st.number_input("Ingresar Meta Soles (S/):", min_value=1.0, value=500000.0, step=10000.0)
    
    st.markdown("---")
    st.subheader("📌 Filtros de Visualización")
    
    if not df_ventas.empty:
        años_disponibles = sorted(df_ventas["AÑO"].unique(), reverse=True)
        año_sel = st.selectbox("Año:", años_disponibles, index=0)
        
        meses_map = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
            7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        meses_presentes = sorted(df_ventas[df_ventas["AÑO"] == año_sel]["MES_NUM"].unique())
        index_mes_default = list(meses_map.keys()).index(meses_presentes[-1]) if meses_presentes else 0
        
        # Filtro desplegable de Meses
        mes_num_sel = st.selectbox("Seleccionar Mes:", list(meses_map.keys()), format_func=lambda x: meses_map[x], index=index_mes_default)
        
        # Filtro desplegable de Canal (Hoja) -> Desplegable que se oculta al seleccionar
        canales_unicos = ["TODOS LOS CANALES"] + sorted(df_ventas["CANAL"].unique().tolist())
        canal_sel = st.selectbox("Canal / Hoja Excel:", canales_unicos, index=0)
        
        # Filtro opcional desplegable por cliente
        clientes_unicos = ["TODOS LOS CLIENTES"] + sorted(df_ventas["CLIENTE"].unique().tolist())
        cliente_filtro = st.selectbox("Filtrar Cliente:", clientes_unicos, index=0)
    else:
        st.error("No se encontraron datos en el archivo de Google Drive.")
        st.stop()

# -----------------------------------------------------------------------------
# FILTRADO DE DATOS
# -----------------------------------------------------------------------------
df_filtrado = df_ventas[(df_ventas["AÑO"] == año_sel) & (df_ventas["MES_NUM"] == mes_num_sel)]

if canal_sel != "TODOS LOS CANALES":
    df_filtrado = df_filtrado[df_filtrado["CANAL"] == canal_sel]

if cliente_filtro != "TODOS LOS CLIENTES":
    df_filtrado = df_filtrado[df_filtrado["CLIENTE"] == cliente_filtro]

# -----------------------------------------------------------------------------
# CÁLCULOS Y KPIS
# -----------------------------------------------------------------------------
venta_acumulada_mes = df_filtrado["MONTO_SOLES"].sum()
unidades_vendidas_mes = df_filtrado["CANTIDAD"].sum()
monto_falta_meta = meta_mensual - venta_acumulada_mes
pct_avance = (venta_acumulada_mes / meta_mensual) * 100 if meta_mensual > 0 else 0

dias_del_mes = calendar.monthrange(año_sel, mes_num_sel)[1]
dias_transcurridos = df_filtrado["DIA"].max() if not df_filtrado.empty else 1
promedio_diario = venta_acumulada_mes / max(dias_transcurridos, 1)
proyeccion_cierre = promedio_diario * dias_del_mes

# -----------------------------------------------------------------------------
# VISUALIZACIÓN DE TARJETAS KPI (COMPACTAS)
# -----------------------------------------------------------------------------
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

with kpi1:
    st.metric("🎯 Meta Mensual", f"S/ {meta_mensual:,.0f}")

with kpi2:
    st.metric("💰 Venta Acum. Mes", f"S/ {venta_acumulada_mes:,.0f}")

with kpi3:
    if monto_falta_meta > 0:
        st.metric("⏳ Falta para Meta", f"S/ {monto_falta_meta:,.0f}", delta=f"-S/ {monto_falta_meta:,.0f}", delta_color="inverse")
    else:
        st.metric("🎉 Meta Alcanzada", f"S/ {abs(monto_falta_meta):,.0f}", delta="Superado", delta_color="normal")

with kpi4:
    st.metric("📈 % Avance", f"{pct_avance:.1f}%")

with kpi5:
    st.metric("🚀 Proyección Cierre", f"S/ {proyeccion_cierre:,.0f}", delta=f"Día: S/ {promedio_diario:,.0f}")

st.progress(min(pct_avance / 100, 1.0))
st.markdown("---")

# -----------------------------------------------------------------------------
# GRÁFICOS ULTRA-COMPACTOS (FIT TO ONE SCREEN - HEIGHT 230px)
# -----------------------------------------------------------------------------
col_top1, col_top2 = st.columns([6, 4])

with col_top1:
    st.caption("📈 **Evolución Diaria y Venta Acumulada del Mes**")
    if not df_filtrado.empty:
        df_diario = df_filtrado.groupby("DIA")["MONTO_SOLES"].sum().reset_index()
        df_diario["ACUMULADO"] = df_diario["MONTO_SOLES"].cumsum()
        
        fig_diario = go.Figure()
        fig_diario.add_trace(go.Bar(
            x=df_diario["DIA"], y=df_diario["MONTO_SOLES"],
            name="Diario (S/)", marker_color='#1E88E5'
        ))
        fig_diario.add_trace(go.Scatter(
            x=df_diario["DIA"], y=df_diario["ACUMULADO"],
            name="Acumulado", mode='lines+markers',
            line=dict(color='#2ECC71', width=2), yaxis="y2"
        ))
        fig_diario.update_layout(
            height=230,
            margin=dict(l=10, r=10, t=10, b=25),
            xaxis=dict(title="Día"),
            yaxis=dict(title="Soles (S/)"),
            yaxis2=dict(overlaying="y", side="right"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10))
        )
        st.plotly_chart(fig_diario, use_container_width=True)
    else:
        st.info("Sin datos para los filtros seleccionados.")

with col_top2:
    st.caption("🏆 **Top Clientes del Mes**")
    if not df_filtrado.empty:
        df_top_cli = df_filtrado.groupby("CLIENTE")["MONTO_SOLES"].sum().reset_index()
        df_top_cli = df_top_cli.sort_values(by="MONTO_SOLES", ascending=True).tail(6)
        
        fig_cli = px.bar(
            df_top_cli, x="MONTO_SOLES", y="CLIENTE",
            orientation='h', text_auto='.2s',
            color="MONTO_SOLES", color_continuous_scale="Blues"
        )
        fig_cli.update_layout(
            height=230,
            margin=dict(l=10, r=10, t=10, b=25),
            xaxis_title=None, yaxis_title=None,
            showlegend=False, coloraxis_showscale=False
        )
        st.plotly_chart(fig_cli, use_container_width=True)

col_bot1, col_bot2 = st.columns(2)

with col_bot1:
    st.caption("📦 **Ventas por Categoría / Tipo de Producto**")
    if not df_filtrado.empty:
        df_prod = df_filtrado.groupby("PRODUCTO")["MONTO_SOLES"].sum().reset_index()
        df_prod = df_prod.sort_values(by="MONTO_SOLES", ascending=False).head(6)
        fig_prod = px.pie(df_prod, values="MONTO_SOLES", names="PRODUCTO", hole=0.45)
        fig_prod.update_layout(
            height=220,
            margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(font=dict(size=9))
        )
        st.plotly_chart(fig_prod, use_container_width=True)

with col_bot2:
    st.caption("🏪 **Comparativo por Canal de Distribución**")
    if not df_filtrado.empty:
        df_canal = df_filtrado.groupby("CANAL")["MONTO_SOLES"].sum().reset_index()
        fig_canal = px.bar(df_canal, x="CANAL", y="MONTO_SOLES", color="CANAL", text_auto='.2s')
        fig_canal.update_layout(
            height=220,
            margin=dict(l=10, r=10, t=10, b=25),
            xaxis_title=None, yaxis_title=None,
            showlegend=False
        )
        st.plotly_chart(fig_canal, use_container_width=True)
