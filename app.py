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

# Estilos CSS estilo Power BI
st.markdown('''
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
            padding-left: 1.5rem;
            padding-right: 1.5rem;
            max-width: 100%;
        }
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
            padding: 10px 18px;
            border-radius: 6px;
            margin-bottom: 15px;
        }
        .header-title h3 {
            margin: 0;
            color: white;
            font-size: 1.3rem;
        }
    </style>
''', unsafe_allow_html=True)

st.markdown('''
    <div class="header-title">
        <h3>📊 CENTRO DE CONTROL COMERCIAL & METAS MENSUALES</h3>
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
            st.error(f"Error al acceder al archivo de Google Drive (Status Code: {res.status_code}). Verifica los permisos del enlace.")
            return pd.DataFrame()
        
        hojas_dict = pd.read_excel(io.BytesIO(res.content), sheet_name=None)
        hojas_a_ignorar = ["PARAMETROS", "PLANTILLA", "RESUMEN", "METAS"]
        dfs_consolidados = []
        
        for nombre_hoja, df in hojas_dict.items():
            if nombre_hoja.strip().upper() in hojas_a_ignorar or df.empty:
                continue
            
            # Limpiar nombres de columnas
            df.columns = [str(col).strip() for col in df.columns]
            cols_clean = {c: str(c).strip().lower() for c in df.columns}
            
            # Nombre del canal desde la pestaña
            df["CANAL_ORIGEN"] = nombre_hoja.strip()
            
            # Mapeo dinámico de columnas del archivo BD_Cuentas_Clave
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
                
                # Conversión limpia de Unidades
                if col_cantidad:
                    df_temp["CANTIDAD"] = pd.to_numeric(df[col_cantidad], errors='coerce').fillna(1)
                else:
                    df_temp["CANTIDAD"] = 1
                
                # Conversión limpia de Soles
                if df[col_monto].dtype == object:
                    df_temp["MONTO_SOLES"] = pd.to_numeric(df[col_monto].astype(str).str.replace('S/', '', regex=False).str.replace(',', '', regex=False).str.strip(), errors='coerce').fillna(0)
                else:
                    df_temp["MONTO_SOLES"] = pd.to_numeric(df[col_monto], errors='coerce').fillna(0)
                
                # Filtrar registros válidos con fechas
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
# SIDEBAR: FILTROS Y CONFIGURACIÓN DE METAS
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Configuración & Filtros")
    
    if st.button("🔄 Actualizar Datos desde Drive", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    st.markdown("---")
    st.subheader("🎯 Meta Comercial del Mes")
    meta_mensual = st.number_input("Ingresar Meta Soles (S/):", min_value=1.0, value=500000.0, step=10000.0)
    
    st.markdown("---")
    st.subheader("📌 Filtros de Visualización")
    
    if not df_ventas.empty:
        # Selección de Año y Mes
        años_disponibles = sorted(df_ventas["AÑO"].unique(), reverse=True)
        año_sel = st.selectbox("Año:", años_disponibles, index=0)
        
        meses_map = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
            7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        meses_presentes = sorted(df_ventas[df_ventas["AÑO"] == año_sel]["MES_NUM"].unique())
        
        # Seleccionar por defecto el último mes con datos
        index_mes_default = list(meses_map.keys()).index(meses_presentes[-1]) if meses_presentes else 0
        mes_num_sel = st.selectbox("Seleccionar Mes:", list(meses_map.keys()), format_func=lambda x: meses_map[x], index=index_mes_default)
        
        # Canales detectados automáticamente desde las hojas del Excel
        canales_unicos = sorted(df_ventas["CANAL"].unique().tolist())
        canales_sel = st.multiselect("Canal / Hoja:", canales_unicos, default=canales_unicos)
        
        # Filtro opcional por cliente
        clientes_unicos = sorted(df_ventas["CLIENTE"].unique().tolist())
        cliente_filtro = st.multiselect("Filtrar Cliente (Opcional):", clientes_unicos, default=[])
    else:
        st.error("No se encontraron datos en el archivo de Google Drive.")
        st.stop()

# -----------------------------------------------------------------------------
# FILTRADO DE DATOS PARA EL MES EN CURSO
# -----------------------------------------------------------------------------
df_filtrado = df_ventas[(df_ventas["AÑO"] == año_sel) & (df_ventas["MES_NUM"] == mes_num_sel)]

if canales_sel:
    df_filtrado = df_filtrado[df_filtrado["CANAL"].isin(canales_sel)]

if cliente_filtro:
    df_filtrado = df_filtrado[df_filtrado["CLIENTE"].isin(cliente_filtro)]

# -----------------------------------------------------------------------------
# CÁLCULOS Y KPIS
# -----------------------------------------------------------------------------
venta_acumulada_mes = df_filtrado["MONTO_SOLES"].sum()
unidades_vendidas_mes = df_filtrado["CANTIDAD"].sum()
monto_falta_meta = meta_mensual - venta_acumulada_mes
pct_avance = (venta_acumulada_mes / meta_mensual) * 100 if meta_mensual > 0 else 0

# Cálculo de Run-Rate / Proyección de Cierre de Mes
dias_del_mes = calendar.monthrange(año_sel, mes_num_sel)[1]
dias_transcurridos = df_filtrado["DIA"].max() if not df_filtrado.empty else 1
promedio_diario = venta_acumulada_mes / max(dias_transcurridos, 1)
proyeccion_cierre = promedio_diario * dias_del_mes

# -----------------------------------------------------------------------------
# VISUALIZACIÓN DE TARJETAS KPI
# -----------------------------------------------------------------------------
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

with kpi1:
    st.metric("🎯 Meta Mensual", f"S/ {meta_mensual:,.2f}")

with kpi2:
    st.metric("💰 Venta Acum. Mes", f"S/ {venta_acumulada_mes:,.2f}")

with kpi3:
    if monto_falta_meta > 0:
        st.metric("⏳ Falta para Meta", f"S/ {monto_falta_meta:,.2f}", delta=f"-S/ {monto_falta_meta:,.2f}", delta_color="inverse")
    else:
        st.metric("🎉 Meta Alcanzada", f"S/ {abs(monto_falta_meta):,.2f}", delta="Superado", delta_color="normal")

with kpi4:
    st.metric("📈 % Avance", f"{pct_avance:.1f}%")

with kpi5:
    st.metric("🚀 Proyección Cierre", f"S/ {proyeccion_cierre:,.2f}", delta=f"Prom. Día: S/ {promedio_diario:,.0f}")

# Barra de Progreso Visual
st.progress(min(pct_avance / 100, 1.0))

st.markdown("---")

# -----------------------------------------------------------------------------
# GRÁFICOS PRINCIPALES
# -----------------------------------------------------------------------------
col_left, col_right = st.columns([6, 4])

with col_left:
    st.subheader("📈 Evolución Diaria y Venta Acumulada del Mes")
    if not df_filtrado.empty:
        df_diario = df_filtrado.groupby("DIA")["MONTO_SOLES"].sum().reset_index()
        df_diario["ACUMULADO"] = df_diario["MONTO_SOLES"].cumsum()
        
        fig_diario = go.Figure()
        
        # Barras de venta diaria
        fig_diario.add_trace(go.Bar(
            x=df_diario["DIA"],
            y=df_diario["MONTO_SOLES"],
            name="Venta Diaria (S/)",
            marker_color='#1E88E5'
        ))
        
        # Línea de venta acumulada
        fig_diario.add_trace(go.Scatter(
            x=df_diario["DIA"],
            y=df_diario["ACUMULADO"],
            name="Acumulado Mes (S/)",
            mode='lines+markers',
            line=dict(color='#2ECC71', width=3),
            yaxis="y2"
        ))
        
        fig_diario.update_layout(
            xaxis=dict(title="Día del Mes"),
            yaxis=dict(title="Venta Diaria Soles (S/)"),
            yaxis2=dict(title="Acumulado Soles (S/)", overlaying="y", side="right"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_diario, use_container_width=True)
    else:
        st.info("No hay ventas registradas para el mes y filtros seleccionados.")

with col_right:
    st.subheader("🏆 Top Clientes del Mes")
    if not df_filtrado.empty:
        df_top_cli = df_filtrado.groupby("CLIENTE")["MONTO_SOLES"].sum().reset_index()
        df_top_cli = df_top_cli.sort_values(by="MONTO_SOLES", ascending=True).tail(8)
        
        fig_cli = px.bar(
            df_top_cli, x="MONTO_SOLES", y="CLIENTE",
            orientation='h',
            text_auto='.2s',
            labels={"MONTO_SOLES": "Soles (S/)", "CLIENTE": "Cliente"},
            color="MONTO_SOLES",
            color_continuous_scale="Blues"
        )
        fig_cli.update_layout(showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig_cli, use_container_width=True)

st.markdown("---")

col_bot1, col_bot2 = st.columns(2)

with col_bot1:
    st.subheader("📦 Ventas por Categoría / Tipo de Producto")
    if not df_filtrado.empty:
        df_prod = df_filtrado.groupby("PRODUCTO")["MONTO_SOLES"].sum().reset_index()
        df_prod = df_prod.sort_values(by="MONTO_SOLES", ascending=False).head(10)
        fig_prod = px.pie(df_prod, values="MONTO_SOLES", names="PRODUCTO", hole=0.4, title="Top Productos Vendidos")
        st.plotly_chart(fig_prod, use_container_width=True)

with col_bot2:
    st.subheader("🏪 Comparativo por Canal (Hojas de Excel)")
    if not df_filtrado.empty:
        df_canal = df_filtrado.groupby("CANAL")["MONTO_SOLES"].sum().reset_index()
        fig_canal = px.bar(df_canal, x="CANAL", y="MONTO_SOLES", color="CANAL", text_auto='.2s')
        fig_canal.update_layout(showlegend=False)
        st.plotly_chart(fig_canal, use_container_width=True)
