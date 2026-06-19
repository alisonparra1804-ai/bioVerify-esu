import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time
import io

# ============================================================
# CONFIGURACIÓN
# ============================================================
FIREBASE_URL = "https://verificacion-electrobisturi-default-rtdb.firebaseio.com"

# Usuarios del sistema
USERS = {
    "aparrag3@est.ups.edu.ec": {
        "password": "BioVerify2026",
        "nombre": "Alison Parra",
        "rol": "Estudiante"
    },
    "admin@bioVerify.com": {
        "password": "admin2026",
        "nombre": "Administrador",
        "rol": "Admin"
    }
}

st.set_page_config(
    page_title="BioVerify ESU",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS PERSONALIZADO
# ============================================================
st.markdown("""
<style>
    /* Fondo principal */
    .stApp {
        background-color: #0A0E1A;
        color: #E8EAF0;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0D1117;
        border-right: 1px solid #1E3A5F;
    }
    
    /* Tarjetas de métricas */
    [data-testid="stMetric"] {
        background-color: #0D1B2A;
        border: 1px solid #1E3A5F;
        border-radius: 12px;
        padding: 16px;
    }
    
    /* Título principal */
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #00BCD4;
        letter-spacing: -0.5px;
    }
    
    /* Subtítulo */
    .sub-title {
        font-size: 0.9rem;
        color: #78909C;
        margin-top: -10px;
    }
    
    /* Badge de estado */
    .badge-cumple {
        background-color: #1B5E20;
        color: #A5D6A7;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    .badge-no-cumple {
        background-color: #B71C1C;
        color: #FFCDD2;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }

    /* Login card */
    .login-card {
        background-color: #0D1B2A;
        border: 1px solid #1E3A5F;
        border-radius: 16px;
        padding: 40px;
        max-width: 420px;
        margin: auto;
    }

    /* Botones */
    .stButton > button {
        background-color: #00BCD4;
        color: #0A0E1A;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 10px 24px;
        width: 100%;
    }
    
    .stButton > button:hover {
        background-color: #0097A7;
        color: white;
    }

    /* Divider */
    hr {
        border-color: #1E3A5F;
    }

    /* Input fields */
    .stTextInput > div > div > input {
        background-color: #0D1B2A;
        border: 1px solid #1E3A5F;
        color: #E8EAF0;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# FUNCIONES DE FIREBASE
# ============================================================

def get_firebase_data():
    try:
        url = f"{FIREBASE_URL}/equipos.json"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def get_equipos():
    try:
        url = f"{FIREBASE_URL}/equipos.json"
        response = requests.get(url, timeout=5)
        if response.status_code == 200 and response.json():
            return list(response.json().keys())
        return []
    except:
        return []

def registrar_equipo(equipo_id, datos):
    try:
        url = f"{FIREBASE_URL}/equipos/{equipo_id}/info.json"
        response = requests.put(url, json=datos, timeout=5)
        return response.status_code == 200
    except:
        return False

def parse_pruebas(data):
    rows = []
    if not data:
        return pd.DataFrame()
    for equipo_id, equipo_data in data.items():
        if "pruebas" not in equipo_data:
            continue
        for prueba_id, prueba in equipo_data["pruebas"].items():
            rows.append({
                "equipo": equipo_id,
                "prueba": prueba_id,
                "fecha": prueba.get("fecha", ""),
                "hora_inicio": prueba.get("hora_inicio", ""),
                "hora_fin": prueba.get("hora_fin", ""),
                "duracion_seg": prueba.get("duracion_seg", 0),
                "modo": prueba.get("modo", ""),
                "corriente_rms": prueba.get("corriente_rms", 0),
                "temperatura": prueba.get("temperatura", 0),
            })
    return pd.DataFrame(rows)

# ============================================================
# SISTEMA DE LOGIN
# ============================================================

def login_page():
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style='text-align: center; margin-bottom: 30px;'>
            <span style='font-size: 3rem;'>⚡</span>
            <h1 style='color: #00BCD4; font-size: 2rem; margin: 0;'>BioVerify ESU</h1>
            <p style='color: #78909C; font-size: 0.9rem;'>Sistema de Verificación de Electrobisturí</p>
            <p style='color: #546E7A; font-size: 0.8rem;'>Universidad Politécnica Salesiana · 2026</p>
        </div>
        """, unsafe_allow_html=True)

        with st.container():
            st.markdown("**Correo electrónico**")
            email = st.text_input("", placeholder="usuario@ejemplo.com", key="email_input", label_visibility="collapsed")
            
            st.markdown("**Contraseña**")
            password = st.text_input("", placeholder="••••••••", type="password", key="pass_input", label_visibility="collapsed")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("Iniciar sesión", use_container_width=True):
                if email in USERS and USERS[email]["password"] == password:
                    st.session_state.logged_in = True
                    st.session_state.user_email = email
                    st.session_state.user_nombre = USERS[email]["nombre"]
                    st.session_state.user_rol = USERS[email]["rol"]
                    st.rerun()
                else:
                    st.error("Correo o contraseña incorrectos")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <p style='text-align: center; color: #546E7A; font-size: 0.75rem;'>
        Alison N. Parra Guano · Carrera de Biomedicina · UPS Quito
        </p>
        """, unsafe_allow_html=True)

# ============================================================
# PÁGINA: NUEVO EQUIPO
# ============================================================

def pagina_nuevo_equipo():
    st.markdown("## ➕ Registrar Nuevo Equipo")
    st.markdown("Completa los datos del equipo electroquirúrgico a registrar.")
    st.divider()

    with st.form("form_nuevo_equipo"):
        col1, col2 = st.columns(2)
        
        with col1:
            nombre = st.text_input("Nombre del equipo *", placeholder="ej. DINATECH-002")
            marca = st.text_input("Marca *", placeholder="ej. DINATECH, VALMED, ERBE")
            modelo = st.text_input("Modelo", placeholder="ej. ESU-300")
            serie = st.text_input("Número de serie", placeholder="ej. SN-2024-001")
        
        with col2:
            ubicacion = st.text_input("Ubicación", placeholder="ej. Quirófano 3, Lab Biomédica")
            responsable = st.text_input("Responsable", placeholder="Nombre del técnico o biomédico")
            ultimo_mant = st.date_input("Fecha último mantenimiento")
            tipo = st.selectbox("Tipo de equipo", ["Electrobisturí real", "Simulador de prueba"])

        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("✅ Registrar equipo", use_container_width=True)
        
        if submitted:
            if not nombre or not marca:
                st.error("El nombre y la marca son obligatorios")
            else:
                datos = {
                    "nombre": nombre,
                    "marca": marca,
                    "modelo": modelo,
                    "serie": serie,
                    "ubicacion": ubicacion,
                    "responsable": responsable,
                    "ultimo_mantenimiento": str(ultimo_mant),
                    "tipo": tipo,
                    "registrado_por": st.session_state.user_nombre,
                    "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                if registrar_equipo(nombre, datos):
                    st.success(f"✅ Equipo **{nombre}** registrado correctamente en Firebase")
                else:
                    st.error("Error al registrar. Verifica la conexión a Firebase.")

# ============================================================
# PÁGINA: DASHBOARD PRINCIPAL
# ============================================================

def pagina_dashboard():
    st.markdown("""
    <div>
        <span class='main-title'>⚡ BioVerify ESU</span><br>
        <span class='sub-title'>Dispositivo portátil de verificación del electrobisturí · Universidad Politécnica Salesiana</span>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    # Controles
    col_r, col_a, col_s = st.columns([1, 2, 3])
    with col_r:
        st.button("🔄 Actualizar", use_container_width=True)
    with col_a:
        auto_refresh = st.toggle("Auto-actualizar cada 5s", value=False)

    # Cargar datos
    data = get_firebase_data()
    df = parse_pruebas(data)

    with col_s:
        if df.empty:
            st.warning("⚠️ Sin datos en Firebase todavía")
        else:
            st.success(f"✅ {len(df)} prueba(s) registrada(s)")

    if not df.empty:
        # ── MÉTRICAS ──
        st.subheader("📊 Resumen General")
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric("Corriente RMS promedio", f"{df['corriente_rms'].mean():.3f} A", f"Máx: {df['corriente_rms'].max():.3f} A")
        with c2:
            st.metric("Temperatura promedio", f"{df['temperatura'].mean():.1f} °C", f"Máx: {df['temperatura'].max():.1f} °C")
        with c3:
            st.metric("Duración promedio", f"{df['duracion_seg'].mean():.1f} s")
        with c4:
            modos = df['modo'].value_counts()
            st.metric("Pruebas de corte", int(modos.get("corte", 0)))
        with c5:
            st.metric("Pruebas de coagulación", int(modos.get("coagulacion", 0)))

        st.divider()

        # ── FILTROS ──
        st.subheader("🔍 Filtros")
        cf1, cf2 = st.columns(2)
        with cf1:
            equipos_disp = ["Todos"] + list(df["equipo"].unique())
            equipo_sel = st.selectbox("Equipo", equipos_disp)
        with cf2:
            modos_disp = ["Todos"] + list(df["modo"].unique())
            modo_sel = st.selectbox("Modo", modos_disp)

        df_f = df.copy()
        if equipo_sel != "Todos":
            df_f = df_f[df_f["equipo"] == equipo_sel]
        if modo_sel != "Todos":
            df_f = df_f[df_f["modo"] == modo_sel]

        st.divider()

        # ── GRÁFICAS ──
        st.subheader("📈 Análisis por Prueba")
        cg1, cg2 = st.columns(2)

        with cg1:
            promedio = df_f["corriente_rms"].mean()
            fig_c = go.Figure()
            fig_c.add_trace(go.Bar(
                x=df_f["prueba"], y=df_f["corriente_rms"],
                marker_color="#00BCD4", text=df_f["corriente_rms"].round(3),
                textposition="outside"
            ))
            fig_c.add_hline(y=promedio * 1.2, line_dash="dash", line_color="#F44336", annotation_text="+20% IEC")
            fig_c.add_hline(y=promedio * 0.8, line_dash="dash", line_color="#FF9800", annotation_text="-20% IEC")
            fig_c.update_layout(
                title="Corriente RMS por Prueba",
                xaxis_title="Prueba", yaxis_title="A",
                paper_bgcolor="#0D1B2A", plot_bgcolor="#0D1B2A",
                font_color="#E8EAF0", height=350, showlegend=False
            )
            st.plotly_chart(fig_c, use_container_width=True)

        with cg2:
            colores = ["#F44336" if t > 100 else "#FF9800" if t > 50 else "#4CAF50" for t in df_f["temperatura"]]
            fig_t = go.Figure()
            fig_t.add_trace(go.Bar(
                x=df_f["prueba"], y=df_f["temperatura"],
                marker_color=colores, text=df_f["temperatura"].round(1),
                textposition="outside"
            ))
            fig_t.add_hline(y=50, line_dash="dash", line_color="#FF9800", annotation_text="50°C residual")
            fig_t.add_hline(y=255, line_dash="dash", line_color="#F44336", annotation_text="255°C máx")
            fig_t.update_layout(
                title="Temperatura por Prueba",
                xaxis_title="Prueba", yaxis_title="°C",
                paper_bgcolor="#0D1B2A", plot_bgcolor="#0D1B2A",
                font_color="#E8EAF0", height=350, showlegend=False
            )
            st.plotly_chart(fig_t, use_container_width=True)

        st.divider()

        # ── GAUGES ──
        st.subheader("🎯 Última Medición")
        cv1, cv2 = st.columns(2)
        promedio_c = df_f["corriente_rms"].mean()
        ultima_c = df_f["corriente_rms"].iloc[-1]
        ultima_t = df_f["temperatura"].iloc[-1]

        with cv1:
            fig_gc = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=ultima_c,
                title={"text": "Corriente RMS (A)", "font": {"color": "#E8EAF0"}},
                delta={"reference": promedio_c},
                gauge={
                    "axis": {"range": [0, df_f["corriente_rms"].max() * 1.5], "tickcolor": "#78909C"},
                    "bar": {"color": "#00BCD4"},
                    "bgcolor": "#0D1B2A",
                    "steps": [
                        {"range": [0, promedio_c * 0.8], "color": "#1A237E"},
                        {"range": [promedio_c * 0.8, promedio_c * 1.2], "color": "#1B5E20"},
                        {"range": [promedio_c * 1.2, df_f["corriente_rms"].max() * 1.5], "color": "#B71C1C"},
                    ],
                }
            ))
            fig_gc.update_layout(height=300, paper_bgcolor="#0D1B2A", font_color="#E8EAF0")
            st.plotly_chart(fig_gc, use_container_width=True)

        with cv2:
            fig_gt = go.Figure(go.Indicator(
                mode="gauge+number",
                value=ultima_t,
                title={"text": "Temperatura (°C)", "font": {"color": "#E8EAF0"}},
                gauge={
                    "axis": {"range": [0, 300], "tickcolor": "#78909C"},
                    "bar": {"color": "#F44336"},
                    "bgcolor": "#0D1B2A",
                    "steps": [
                        {"range": [0, 50], "color": "#1B5E20"},
                        {"range": [50, 100], "color": "#E65100"},
                        {"range": [100, 255], "color": "#B71C1C"},
                        {"range": [255, 300], "color": "#4A0000"},
                    ],
                }
            ))
            fig_gt.update_layout(height=300, paper_bgcolor="#0D1B2A", font_color="#E8EAF0")
            st.plotly_chart(fig_gt, use_container_width=True)

        st.divider()

        # ── ANÁLISIS ESTADÍSTICO IEC 60601-2-2 ──
        st.subheader("📋 Análisis Estadístico · IEC 60601-2-2")

        promedio_c = df_f["corriente_rms"].mean()
        std_c = df_f["corriente_rms"].std()
        cv_c = (std_c / promedio_c * 100) if promedio_c > 0 else 0

        df_f = df_f.copy()
        df_f["error_relativo_%"] = abs((df_f["corriente_rms"] - promedio_c) / promedio_c * 100).round(2)
        df_f["cumple_norma"] = df_f["error_relativo_%"].apply(lambda x: "✅ Cumple" if x <= 20 else "❌ No cumple")

        cs1, cs2, cs3, cs4 = st.columns(4)
        with cs1:
            st.metric("Corriente promedio", f"{promedio_c:.4f} A")
        with cs2:
            st.metric("Desviación estándar", f"{std_c:.4f} A")
        with cs3:
            st.metric("Coef. de variación", f"{cv_c:.2f} %")
        with cs4:
            cumple_count = (df_f["error_relativo_%"] <= 20).sum()
            total = len(df_f)
            color = "normal" if cumple_count == total else "inverse"
            st.metric("Pruebas dentro del ±20%", f"{cumple_count}/{total}")

        st.divider()

        # ── TABLA ──
        st.subheader("🗂️ Registro de Pruebas")
        st.dataframe(
            df_f[[
                "equipo", "prueba", "fecha", "hora_inicio", "hora_fin",
                "duracion_seg", "modo", "corriente_rms", "temperatura",
                "error_relativo_%", "cumple_norma"
            ]].rename(columns={
                "equipo": "Equipo", "prueba": "Prueba", "fecha": "Fecha",
                "hora_inicio": "Inicio", "hora_fin": "Fin",
                "duracion_seg": "Duración (s)", "modo": "Modo",
                "corriente_rms": "Corriente RMS (A)", "temperatura": "Temperatura (°C)",
                "error_relativo_%": "Error (%)", "cumple_norma": "IEC 60601-2-2"
            }),
            use_container_width=True, hide_index=True
        )

        csv = df_f.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Descargar CSV",
            data=csv,
            file_name=f"bioVerify_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

    else:
        st.info("📡 Esperando datos del ESP32... Enciende el dispositivo y activa el electrobisturí.")

    if auto_refresh:
        time.sleep(5)
        st.rerun()

# ============================================================
# MAIN - CONTROL DE SESIÓN
# ============================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login_page()
else:
    # Sidebar
    with st.sidebar:
        st.markdown(f"""
        <div style='padding: 16px 0;'>
            <p style='color: #78909C; font-size: 0.8rem; margin: 0;'>Sesión activa</p>
            <p style='color: #00BCD4; font-weight: 600; margin: 4px 0;'>{st.session_state.user_nombre}</p>
            <p style='color: #546E7A; font-size: 0.75rem; margin: 0;'>{st.session_state.user_rol}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        pagina = st.radio(
            "Navegación",
            ["📊 Dashboard", "➕ Nuevo Equipo"],
            label_visibility="collapsed"
        )
        
        st.divider()
        
        if st.button("🚪 Cerrar sesión", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <p style='color: #37474F; font-size: 0.7rem; text-align: center;'>
        BioVerify ESU v2.0<br>
        Alison N. Parra Guano<br>
        UPS · Biomedicina · 2026
        </p>
        """, unsafe_allow_html=True)

    if pagina == "📊 Dashboard":
        pagina_dashboard()
    elif pagina == "➕ Nuevo Equipo":
        pagina_nuevo_equipo()
