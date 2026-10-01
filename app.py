import streamlit as st

st.set_page_config(
    page_title="Centro de Control Operativo",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Centro de Control Comercial & Financiero")
st.markdown("---")

st.markdown("""
Bienvenido al **Sistema de Control Integrado**. Utiliza el menú lateral izquierdo para navegar entre los módulos disponibles:

### 📑 Módulos Disponibles:
1. **📊 Ventas y Metas:** 
   - Seguimiento de cumplimiento de metas mensuales.
   - Avance en ventas por cliente, canal y producto.
   - Proyección de cierre de mes (Run-Rate) e historial diario.

2. **💳 Cobranzas y Créditos:** *(Próximamente)*
   - Control de saldo pendiente y facturación por N° de Documento.
   - Antigüedad de deuda por cliente y tramos de días.
""")

st.info("💡 **Consejo:** Utiliza el botón **'🔄 Actualizar Datos'** dentro de cada módulo para sincronizar los cambios de Google Drive en tiempo real.")
