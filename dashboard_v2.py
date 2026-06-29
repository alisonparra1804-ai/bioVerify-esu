import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time
import base64
import hashlib
import os

FIREBASE_URL = "https://verificacion-electrobisturi-default-rtdb.firebaseio.com"
TEMP_AMARILLA = 50
TEMP_ROJA = 255
ERROR_MAXIMO = 20

# ── TABLA DE REFERENCIA ESA620 POR POTENCIA DE PERILLA ──
# Formato: {modo: {potencia_perilla_W: corriente_ESA620_A}}
# Fuente: mediciones experimentales con Fluke True-RMS sobre DINATECH BC-50D
# El operador selecciona la potencia de perilla en el dashboard para
# obtener la comparación correcta contra el ESA620.

REF_ESA620 = {
    "corte": {
        10:  0.600,
        20:  0.800,
        40:  1.100,
        60:  1.500,
        80:  1.800,
        100: 1.900,
        120: 1.925,
        140: 2.000,
        160: 2.650,
        180: 2.580,
        200: 3.000,
    },
    "coagulacion": {
        10:  0.400,
        20:  0.400,
        40:  0.650,
        60:  0.750,
        80:  0.900,
        100: 1.200,
        120: 1.300,
        140: 1.350,
        160: 1.400,
        180: 1.700,
        200: 1.900,
    }
}

NIVELES_POTENCIA = [10, 20, 40, 60, 80, 100, 120, 140, 160, 180, 200]

def get_referencia_esa620(modo, potencia_perilla):
    """Obtiene la corriente de referencia ESA620 para la potencia de perilla seleccionada."""
    refs = REF_ESA620.get(str(modo).lower(), {})
    return refs.get(int(potencia_perilla), None)

def calcular_error(corriente_medida, modo, potencia_perilla=None):
    """Calcula error relativo comparando corriente medida vs referencia ESA620."""
    if potencia_perilla is None:
        return None
    i_ref = get_referencia_esa620(modo, potencia_perilla)
    if i_ref and i_ref > 0:
        return round(abs((corriente_medida - i_ref) / i_ref * 100), 2)
    return None

st.set_page_config(
    page_title="BioVerify ESU",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

* { font-family: 'Inter', sans-serif !important; }

.stApp {
    background-color: #F0F4F8 !important;
    color: #1A202C !important;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0A2540 0%, #0D3260 100%) !important;
    border-right: none !important;
}

[data-testid="stSidebar"] * { color: #fff !important; }

.sidebar-logo-wrap {
    text-align: center;
    padding: 28px 16px 20px;
    border-bottom: 1px solid rgba(255,255,255,0.15);
}

.sidebar-logo-wrap img {
    width: 120px;
    height: 120px;
    border-radius: 50%;
    border: 3px solid #00B4D8;
    margin-bottom: 10px;
}

.sidebar-app-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #00B4D8 !important;
    margin: 0;
}

.sidebar-app-sub {
    font-size: 0.7rem;
    color: rgba(255,255,255,0.6) !important;
    margin: 3px 0 0;
}

.user-info-box {
    background: rgba(255,255,255,0.1);
    border-radius: 8px;
    padding: 10px 14px;
    margin: 12px 16px;
}

.user-info-name {
    font-size: 0.82rem;
    font-weight: 600;
    color: #fff !important;
    margin: 0;
}

.user-info-role {
    font-size: 0.7rem;
    color: rgba(255,255,255,0.6) !important;
    margin: 2px 0 0;
}

[data-testid="stSidebar"] .stRadio label {
    color: rgba(255,255,255,0.85) !important;
    font-size: 0.85rem !important;
    padding: 6px 0 !important;
}

[data-testid="stSidebar"] .stRadio label:hover {
    color: #00B4D8 !important;
}

.page-header {
    background: #fff;
    border-radius: 12px;
    padding: 18px 24px;
    margin-bottom: 18px;
    border: 1px solid #E2E8F0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

.page-title {
    font-size: 1.3rem;
    font-weight: 700;
    color: #1A202C;
    margin: 0;
}

.page-sub {
    font-size: 0.78rem;
    color: #718096;
    margin: 2px 0 0;
}

.kpi-card {
    background: #fff;
    border-radius: 12px;
    padding: 16px 18px;
    border: 1px solid #E2E8F0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    border-top: 4px solid #0F3460;
    height: 100%;
}

.kpi-card.amarillo { border-top-color: #D97706; }
.kpi-card.rojo { border-top-color: #DC2626; }
.kpi-card.azul { border-top-color: #2563EB; }
.kpi-card.gris { border-top-color: #64748B; }

.kpi-label {
    font-size: 0.68rem;
    font-weight: 600;
    color: #718096;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin: 0 0 6px;
}

.kpi-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.8rem;
    font-weight: 700;
    color: #1A202C;
    margin: 0;
    line-height: 1;
}

.kpi-value.verde { color: #0F3460; }
.kpi-value.amarillo { color: #D97706; }
.kpi-value.rojo { color: #DC2626; }

.kpi-unit { font-size: 0.85rem; color: #718096; margin-left: 3px; }
.kpi-sub { font-size: 0.7rem; color: #A0AEC0; margin: 5px 0 0; }

.alarma-box {
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 12px;
    border-left: 5px solid;
    font-size: 0.82rem;
}

.alarma-verde { background: #F0F7FF; border-color: #0F3460; color: #0A2347; }
.alarma-amarilla { background: #FFFBEB; border-color: #D97706; color: #78350F; }
.alarma-roja { background: #FEF2F2; border-color: #DC2626; color: #7F1D1D; }

.chart-card {
    background: #fff;
    border-radius: 12px;
    padding: 16px;
    border: 1px solid #E2E8F0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

.chart-label {
    font-size: 0.72rem;
    font-weight: 600;
    color: #718096;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin: 0 0 10px;
}

.modo-tag {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-left: 10px;
}

.modo-corte { background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; }
.modo-coag { background: #FEF3C7; color: #92400E; border: 1px solid #FDE68A; }
.modo-standby { background: #F1F5F9; color: #64748B; border: 1px solid #CBD5E1; }

.stButton > button {
    background: linear-gradient(135deg, #0F3460 0%, #0D2D56 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.83rem !important;
}

.stButton > button:hover {
    background: linear-gradient(135deg, #0D2D56 0%, #0A2347 100%) !important;
}

.login-wrap {
    background: linear-gradient(135deg, #F0F7FF 0%, #F0FDF4 100%);
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
}

.form-card {
    background: #fff;
    border-radius: 20px;
    padding: 40px;
    border: 1px solid #E2E8F0;
    box-shadow: 0 8px 32px rgba(0,0,0,0.08);
}

.ts { font-size: 0.7rem; color: #A0AEC0; }
</style>
""", unsafe_allow_html=True)

# ── FIREBASE ──
def fb_get(path):
    try:
        r = requests.get(f"{FIREBASE_URL}/{path}.json", timeout=5)
        return r.json() if r.status_code == 200 else None
    except: return None

def fb_put(path, data):
    try:
        r = requests.put(f"{FIREBASE_URL}/{path}.json", json=data, timeout=5)
        return r.status_code == 200
    except: return False

# Mapeo fijo prueba -> potencia de perilla del electrobisturi
# Corte:       prueba_001..011 = 10,20,40,60,80,100,120,140,160,180,200 W
# Coagulacion: prueba_013..023 = 10,20,40,60,80,100,120,140,160,180,200 W
MAPEO_POTENCIA_PERILLA = {
    "BC-50D": {
        "prueba_001": 10,  "prueba_002": 20,  "prueba_003": 40,
        "prueba_004": 60,  "prueba_005": 80,  "prueba_006": 100,
        "prueba_007": 120, "prueba_008": 140, "prueba_009": 160,
        "prueba_010": 180, "prueba_011": 200,
        "prueba_013": 10,  "prueba_014": 20,  "prueba_015": 40,
        "prueba_016": 60,  "prueba_017": 80,  "prueba_018": 100,
        "prueba_019": 120, "prueba_020": 140, "prueba_021": 160,
        "prueba_022": 180, "prueba_023": 200,
    }
}

def parse_pruebas():
    data = fb_get("equipos")
    rows = []
    if not data: return pd.DataFrame()
    for eq_id, eq_data in data.items():
        if not isinstance(eq_data, dict): continue
        mapeo = MAPEO_POTENCIA_PERILLA.get(eq_id, {})
        for pr_id, pr in eq_data.get("pruebas", {}).items():
            if not isinstance(pr, dict): continue
            pot_perilla = pr.get("potencia_perilla", mapeo.get(pr_id, None))
            rows.append({
                "equipo": eq_id, "prueba": pr_id,
                "fecha": pr.get("fecha",""),
                "modo": pr.get("modo",""),
                "corriente_rms": float(pr.get("corriente_rms", 0)),
                "temperatura": float(pr.get("temperatura", 0)),
                "potencia_w": float(pr.get("potencia_w", pr.get("corriente_rms",0) * 110)),
                "potencia_perilla": int(pot_perilla) if pot_perilla is not None else None,
                "duracion_seg": float(str(pr.get("duracion_seg",0)).strip()),
            })
    return pd.DataFrame(rows)

def get_logo():
    for p in ["assets/LOGO.png","LOGO.png","/mnt/user-data/outputs/LOGO.png"]:
        if os.path.exists(p):
            with open(p,"rb") as f:
                return base64.b64encode(f.read()).decode()
    return None

def verificar_login(email, password):
    hash_pw = hashlib.sha256(password.encode()).hexdigest()
    # Admin por defecto
    if email == "alison.parra@est.ups.edu.ec" and password == "BioVerify2026":
        return True, {"nombre":"Alison Parra","rol":"Investigadora","email":email}
    usuarios = fb_get("usuarios") or {}
    for uid, u in usuarios.items():
        if u.get("email") == email and u.get("password") == hash_pw:
            return True, u
    return False, None

def crear_cuenta(email, password, nombre, rol):
    uid = hashlib.md5(email.encode()).hexdigest()[:8]
    usuarios = fb_get("usuarios") or {}
    for u in usuarios.values():
        if u.get("email") == email:
            return False, "El correo ya esta registrado"
    hash_pw = hashlib.sha256(password.encode()).hexdigest()
    ok = fb_put(f"usuarios/{uid}", {
        "email": email, "password": hash_pw,
        "nombre": nombre, "rol": rol,
        "creado": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    return ok, "ok"

# ── LOGIN ──
def pagina_login():
    logo = get_logo()
    logo_html = f'<img src="data:image/png;base64,{logo}" style="width:110px;height:110px;border-radius:50%;border:3px solid #0F3460;margin-bottom:12px;">' if logo else ""

    col1, col2, col3 = st.columns([1,1.1,1])
    with col2:
        st.markdown(f"""
        <div style="margin-top:50px;background:#fff;border-radius:20px;padding:40px;border:1px solid #E2E8F0;box-shadow:0 8px 32px rgba(0,0,0,0.08);text-align:center;">
            {logo_html}
            <h2 style="color:#1A202C;font-size:1.5rem;margin:0 0 4px;">BioVerify ESU</h2>
            <p style="color:#718096;font-size:0.78rem;margin:0 0 28px;">Sistema de Verificacion de Electrobisturi · UPS Quito</p>
        </div>
        """, unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["Iniciar sesion", "Crear cuenta"])
        with tab1:
            email = st.text_input("Correo", placeholder="usuario@ups.edu.ec", key="li_e")
            pw = st.text_input("Contrasena", type="password", key="li_p")
            if st.button("Ingresar", key="btn_in", use_container_width=True):
                ok, user = verificar_login(email, pw)
                if ok:
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Correo o contrasena incorrectos")

        with tab2:
            nombre = st.text_input("Nombre completo", key="rn")
            email_r = st.text_input("Correo", key="re")
            rol_r = st.selectbox("Rol", ["Biomedico","Investigador","Tecnico","Docente"], key="rr")
            pw_r = st.text_input("Contrasena", type="password", key="rp1")
            pw_r2 = st.text_input("Confirmar contrasena", type="password", key="rp2")
            if st.button("Crear cuenta", key="btn_reg", use_container_width=True):
                if not nombre or not email_r or not pw_r:
                    st.error("Completa todos los campos")
                elif pw_r != pw_r2:
                    st.error("Las contrasenas no coinciden")
                elif len(pw_r) < 6:
                    st.error("Minimo 6 caracteres")
                else:
                    ok, msg = crear_cuenta(email_r, pw_r, nombre, rol_r)
                    if ok: st.success("Cuenta creada. Ya puedes iniciar sesion.")
                    else: st.error(msg)

# ── SIDEBAR ──
def sidebar():
    logo = get_logo()
    logo_html = f'<img src="data:image/png;base64,{logo}" style="width:120px;height:120px;border-radius:50%;border:3px solid #00B4D8;margin-bottom:10px;">' if logo else ""
    user = st.session_state.user

    with st.sidebar:
        st.markdown(f"""
        <div class="sidebar-logo-wrap">
            {logo_html}
            <p class="sidebar-app-title">BioVerify ESU</p>
            <p class="sidebar-app-sub">Verificacion de Electrobisturi</p>
        </div>
        <div class="user-info-box">
            <p class="user-info-name">{user.get('nombre','Usuario')}</p>
            <p class="user-info-role">{user.get('rol','')} · {user.get('email','')}</p>
        </div>
        """, unsafe_allow_html=True)

        nav = st.radio("", ["Panel principal","Equipos","Configuracion remota","Nuevo equipo"],
                       label_visibility="collapsed")

        st.markdown("---")
        if st.button("Cerrar sesion", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()
        st.markdown(f'<p class="ts" style="padding:12px 0;text-align:center;">BioVerify ESU v3.0<br>Alison N. Parra Guano<br>UPS Biomedicina 2026</p>', unsafe_allow_html=True)
    return nav

# ── PANEL PRINCIPAL ──
def panel_principal():
    now = datetime.now().strftime("%d/%m/%Y  %H:%M:%S")
    modo_config = fb_get("config/modo") or "standby"
    tag_class = "modo-corte" if modo_config=="corte" else "modo-coag" if modo_config=="coagulacion" else "modo-standby"

    st.markdown(f"""
    <div class="page-header">
        <div style="display:flex;align-items:center;">
            <div>
                <p class="page-title">Panel principal
                    <span class="modo-tag {tag_class}">{modo_config.upper()}</span>
                </p>
                <p class="page-sub">Monitoreo en tiempo real · Norma IEC 60601-2-2</p>
            </div>
        </div>
        <span class="ts">{now}</span>
    </div>
    """, unsafe_allow_html=True)

    # Selector de modo y potencia de perilla
    cm1, cm2, cm3, cm4 = st.columns([1, 1, 1.5, 2])
    with cm1:
        if st.button("CORTE", use_container_width=True):
            fb_put("config/modo", "corte")
            st.rerun()
    with cm2:
        if st.button("COAGULACION", use_container_width=True):
            fb_put("config/modo", "coagulacion")
            st.rerun()
    with cm3:
        potencia_perilla = st.selectbox(
            "Potencia de perilla (W)",
            options=NIVELES_POTENCIA,
            index=4,  # default 80W
            key="pot_perilla",
            label_visibility="collapsed",
            help="Selecciona la potencia configurada en la perilla del electrobisturi"
        )
        st.markdown(f'<p style="font-size:0.7rem;color:#718096;margin:2px 0 0;text-align:center;">Perilla: {potencia_perilla} W</p>', unsafe_allow_html=True)

    df = parse_pruebas()

    if df.empty:
        st.markdown("""
        <div style="background:#fff;border:1px solid #E2E8F0;border-radius:12px;padding:48px;text-align:center;margin-top:16px;">
            <p style="font-size:1.5rem;font-weight:700;color:#A0AEC0;margin:0">Sin datos del dispositivo</p>
            <p style="color:#CBD5E1;font-size:0.85rem;margin:8px 0 0;">Verifica que el ESP32 este conectado al WiFi y enviando datos a Firebase.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    ultima = df.iloc[-1]
    temp = ultima["temperatura"]

    # Error calculado contra referencia ESA620 usando potencia de perilla seleccionada
    modo_actual = ultima.get("modo", modo_config)
    i_ref_ultima = get_referencia_esa620(modo_actual, potencia_perilla)
    if i_ref_ultima and i_ref_ultima > 0:
        error_c = abs((ultima["corriente_rms"] - i_ref_ultima) / i_ref_ultima * 100)
        prom_c = i_ref_ultima
    else:
        prom_c = df["corriente_rms"].mean()
        error_c = abs((ultima["corriente_rms"] - prom_c) / prom_c * 100) if prom_c > 0 else 0

    # Alarma
    if temp >= TEMP_ROJA or error_c > ERROR_MAXIMO:
        st.markdown(f'<div class="alarma-box alarma-roja"><strong>ALARMA CRITICA</strong> — {"Temperatura "+str(round(temp,1))+"°C supera limite de "+str(TEMP_ROJA)+"°C" if temp>=TEMP_ROJA else "Error de corriente "+str(round(error_c,1))+"% supera limite IEC 60601-2-2 (20%)"}</div>', unsafe_allow_html=True)
    elif temp >= TEMP_AMARILLA or error_c > ERROR_MAXIMO * 0.75:
        st.markdown(f'<div class="alarma-box alarma-amarilla"><strong>ADVERTENCIA</strong> — {"Calor residual "+str(round(temp,1))+"°C supera umbral de "+str(TEMP_AMARILLA)+"°C (Brinkmann 2022)" if temp>=TEMP_AMARILLA else "Error de corriente "+str(round(error_c,1))+"% aproximandose al limite IEC"}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="alarma-box alarma-verde"><strong>Sistema normal</strong> — Temperatura {round(temp,1)}°C · Error corriente {round(error_c,1)}% · Dentro de norma IEC 60601-2-2</div>', unsafe_allow_html=True)

    # KPIs
    color_c = "verde" if error_c <= 15 else "amarillo" if error_c <= ERROR_MAXIMO else "rojo"
    color_t = "verde" if temp < TEMP_AMARILLA else "amarillo" if temp < TEMP_ROJA else "rojo"
    color_card_c = "" if error_c <= 15 else "amarillo" if error_c <= ERROR_MAXIMO else "rojo"
    color_card_t = "" if temp < TEMP_AMARILLA else "amarillo" if temp < TEMP_ROJA else "rojo"
    cumple = df.apply(
        lambda row: calcular_error(row["corriente_rms"], row.get("modo","corte"), row.get("potencia_w",0)) or 0,
        axis=1
    ).apply(lambda e: e <= ERROR_MAXIMO).sum()

    k1,k2,k3,k4,k5 = st.columns(5)
    def kpi(col, label, val, unit, sub, card_c="", val_c=""):
        with col:
            st.markdown(f"""
            <div class="kpi-card {card_c}">
                <p class="kpi-label">{label}</p>
                <p class="kpi-value {val_c}">{val}<span class="kpi-unit">{unit}</span></p>
                <p class="kpi-sub">{sub}</p>
            </div>
            """, unsafe_allow_html=True)

    kpi(k1,"Corriente RMS",f"{ultima['corriente_rms']:.3f}","A",f"Error: {error_c:.1f}%",color_card_c,color_c)
    kpi(k2,"Temperatura Residual",f"{temp:.1f}","C",f"Umbral residual: {TEMP_AMARILLA}°C",color_card_t,color_t)
    kpi(k3,"Potencia estimada",f"{ultima['potencia_w']:.0f}","W","I × Vred","azul","")
    kpi(k4,"Pruebas totales",str(len(df)),"",f"Equipos: {df['equipo'].nunique()}","gris","")
    kpi(k5,"Cumple IEC",f"{cumple}/{len(df)}","",f"Margen ±{ERROR_MAXIMO}%","" if cumple==len(df) else "amarillo","verde" if cumple==len(df) else "amarillo")

    # Graficas
    g1, g2 = st.columns(2)

    with g1:
        st.markdown('<div class="chart-card"><p class="chart-label">Corriente RMS por prueba (A)</p>', unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=list(range(len(df))), y=df["corriente_rms"].tolist(),
            mode="lines+markers",
            line=dict(color="#0F3460", width=2.5),
            marker=dict(size=7, color="#0F3460"),
            fill="tozeroy", fillcolor="rgba(5,150,105,0.08)",
            name="Corriente RMS"
        ))
        if prom_c > 0:
            fig.add_hline(y=prom_c*1.2, line_dash="dash", line_color="#EF4444", line_width=1.5, annotation_text="+20% IEC", annotation_font_size=10)
            fig.add_hline(y=prom_c*0.8, line_dash="dash", line_color="#F59E0B", line_width=1.5, annotation_text="-20% IEC", annotation_font_size=10)
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#718096", height=200,
            margin=dict(t=10,b=10,l=10,r=10), showlegend=False,
            xaxis=dict(showgrid=True, gridcolor="#E2E8F0", tickfont=dict(size=9)),
            yaxis=dict(showgrid=True, gridcolor="#E2E8F0", tickfont=dict(size=9))
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
        st.markdown('</div>', unsafe_allow_html=True)

    with g2:
        st.markdown('<div class="chart-card"><p class="chart-label">Temperatura por prueba (°C)</p>', unsafe_allow_html=True)
        fig2 = go.Figure()
        colores_t = ["#DC2626" if t>=TEMP_ROJA else "#D97706" if t>=TEMP_AMARILLA else "#3B82F6" for t in df["temperatura"]]
        fig2.add_trace(go.Scatter(
            x=list(range(len(df))), y=df["temperatura"].tolist(),
            mode="lines+markers",
            line=dict(color="#3B82F6", width=2.5),
            marker=dict(size=7, color=colores_t),
            fill="tozeroy", fillcolor="rgba(59,130,246,0.08)",
        ))
        fig2.add_hline(y=TEMP_AMARILLA, line_dash="dash", line_color="#F59E0B", line_width=1.5, annotation_text=f"{TEMP_AMARILLA}°C", annotation_font_size=10)
        fig2.add_hline(y=TEMP_ROJA, line_dash="dash", line_color="#EF4444", line_width=1.5, annotation_text=f"{TEMP_ROJA}°C", annotation_font_size=10)
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#718096", height=200,
            margin=dict(t=10,b=10,l=10,r=10), showlegend=False,
            xaxis=dict(showgrid=True, gridcolor="#E2E8F0", tickfont=dict(size=9)),
            yaxis=dict(showgrid=True, gridcolor="#E2E8F0", tickfont=dict(size=9))
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})
        st.markdown('</div>', unsafe_allow_html=True)

    # Tabla compacta — error calculado por fila usando potencia_perilla de cada prueba
    def error_por_fila(row):
        pp = row.get("potencia_perilla", None)
        modo = row.get("modo", "corte")
        i_bv = row["corriente_rms"]
        if pp is not None:
            i_ref = get_referencia_esa620(modo, int(pp))
        else:
            i_ref = get_referencia_esa620(modo, potencia_perilla)
        if i_ref and i_ref > 0:
            return round(abs((i_bv - i_ref) / i_ref * 100), 2)
        return round(abs((i_bv - prom_c) / prom_c * 100), 2) if prom_c > 0 else 0

    df["error_%"] = df.apply(error_por_fila, axis=1)
    df["IEC"] = df["error_%"].apply(lambda x: "Cumple" if x <= ERROR_MAXIMO else "No cumple")

    st.markdown('<div class="chart-card"><p class="chart-label">Registro de pruebas</p>', unsafe_allow_html=True)
    cf1,cf2,cf3 = st.columns([2,2,2])
    with cf1:
        eq_sel = st.selectbox("Equipo",["Todos"]+list(df["equipo"].unique()),label_visibility="collapsed",key="f_eq")
    with cf2:
        mo_sel = st.selectbox("Modo",["Todos"]+list(df["modo"].unique()),label_visibility="collapsed",key="f_mo")
    with cf3:
        st.download_button("Descargar CSV",df.to_csv(index=False).encode("utf-8"),f"bioVerify_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",use_container_width=True)

    df_f = df.copy()
    if eq_sel != "Todos": df_f = df_f[df_f["equipo"]==eq_sel]
    if mo_sel != "Todos": df_f = df_f[df_f["modo"]==mo_sel]

    st.dataframe(
        df_f[["equipo","prueba","fecha","modo","potencia_perilla","corriente_rms","temperatura","potencia_w","error_%","IEC"]].rename(columns={
            "equipo":"Equipo","prueba":"Prueba","fecha":"Fecha","modo":"Modo",
            "potencia_perilla":"Perilla (W)","corriente_rms":"Corriente (A)",
            "temperatura":"T. Residual (°C)","potencia_w":"Potencia red (W)",
            "error_%":"Error (%)","IEC":"IEC 60601-2-2"
        }),
        use_container_width=True, hide_index=True, height=200
    )
    st.markdown('</div>', unsafe_allow_html=True)

# ── EQUIPOS ──
def pagina_equipos():
    st.markdown('<div class="page-header"><div><p class="page-title">Equipos registrados</p><p class="page-sub">Inventario de generadores electroquirurgicos</p></div></div>', unsafe_allow_html=True)
    data = fb_get("equipos")
    if not data:
        st.info("No hay equipos registrados.")
        return
    for eq_id, eq_data in data.items():
        if not isinstance(eq_data, dict): continue
        info = eq_data.get("info", {})
        n = len(eq_data.get("pruebas", {}))
        st.markdown(f"""
        <div style="background:#fff;border:1px solid #E2E8F0;border-radius:12px;padding:18px;margin-bottom:12px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                <strong style="font-size:0.95rem;">{eq_id}</strong>
                <span style="background:#F0F7FF;color:#0F3460;padding:3px 12px;border-radius:20px;font-size:0.72rem;font-weight:600;">{n} prueba(s)</span>
            </div>
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;font-size:0.78rem;">
                <div><span style="color:#718096">Marca</span><br><strong>{info.get('marca','—')}</strong></div>
                <div><span style="color:#718096">Modelo</span><br><strong>{info.get('modelo','—')}</strong></div>
                <div><span style="color:#718096">Serie</span><br><strong>{info.get('serie','—')}</strong></div>
                <div><span style="color:#718096">Ubicacion</span><br><strong>{info.get('ubicacion','—')}</strong></div>
                <div><span style="color:#718096">Responsable</span><br><strong>{info.get('responsable','—')}</strong></div>
                <div><span style="color:#718096">Ultimo mantenimiento</span><br><strong>{info.get('ultimo_mantenimiento','—')}</strong></div>
                <div><span style="color:#718096">Tipo</span><br><strong>{info.get('tipo','—')}</strong></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ── CONFIG REMOTA ──
def pagina_config():
    st.markdown('<div class="page-header"><div><p class="page-title">Configuracion remota</p><p class="page-sub">Ajuste de parametros del ESP32 via Firebase</p></div></div>', unsafe_allow_html=True)
    cfg = fb_get("config") or {}

    st.markdown('<div style="background:#fff;border:1px solid #E2E8F0;border-radius:12px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">', unsafe_allow_html=True)
    c1,c2 = st.columns(2)
    with c1:
        vac = st.number_input("Voltaje de red (V)", 90.0, 250.0, float(cfg.get("gridVoltageConfig",110.0)), 1.0)
        ofs = st.number_input("Offset ADC (V)", 0.0, 3.3, float(cfg.get("adcOffsetVolts",1.65)), 0.01, "%.2f")
    with c2:
        scl = st.number_input("Escala corriente", 0.1, 100.0, float(cfg.get("currentScale",11.4)), 0.1, "%.1f")
        modo = st.selectbox("Modo", ["standby","corte","coagulacion"],
            index=["standby","corte","coagulacion"].index(cfg.get("modo","standby")))

    if st.button("Guardar en Firebase", use_container_width=True):
        ok = fb_put("config", {"gridVoltageConfig":vac,"adcOffsetVolts":ofs,"currentScale":scl,"modo":modo,
            "actualizado":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"por":st.session_state.user.get("nombre","")})
        st.success("Configuracion guardada. El ESP32 la aplicara en el proximo ciclo.") if ok else st.error("Error al guardar.")

    st.markdown("""
    <p style="font-size:0.78rem;color:#718096;margin-top:16px;line-height:1.8;">
    El ESP32 lee estos valores desde Firebase cada 30 segundos y los aplica automaticamente.<br>
    Los cambios se guardan en la EEPROM del dispositivo para persistir tras reinicios.
    </p></div>""", unsafe_allow_html=True)

# ── NUEVO EQUIPO ──
def pagina_nuevo_equipo():
    st.markdown('<div class="page-header"><div><p class="page-title">Nuevo equipo</p><p class="page-sub">Registrar generador electroquirurgico en Firebase</p></div></div>', unsafe_allow_html=True)
    st.markdown('<div style="background:#fff;border:1px solid #E2E8F0;border-radius:12px;padding:24px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">', unsafe_allow_html=True)

    with st.form("f_eq"):
        c1,c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Identificador *", placeholder="DINATECH-002")
            marca = st.text_input("Marca *", placeholder="DINATECH, VALMED, ERBE")
            modelo = st.text_input("Modelo", placeholder="ESU-300B")
            serie = st.text_input("Numero de serie")
        with c2:
            ubicacion = st.text_input("Ubicacion", placeholder="Quirofano 3")
            responsable = st.text_input("Responsable")
            mant = st.date_input("Ultimo mantenimiento")
            tipo = st.selectbox("Tipo", ["Electrobisturi real","Simulador de prueba","Laboratorio"])

        if st.form_submit_button("Registrar equipo", use_container_width=True):
            if not nombre or not marca:
                st.error("Identificador y marca son obligatorios")
            else:
                ok = fb_put(f"equipos/{nombre}/info", {
                    "marca":marca,"modelo":modelo,"serie":serie,
                    "ubicacion":ubicacion,"responsable":responsable,
                    "ultimo_mantenimiento":str(mant),"tipo":tipo,
                    "por":st.session_state.user.get("nombre",""),
                    "fecha":datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                st.success(f"Equipo {nombre} registrado.") if ok else st.error("Error al registrar.")

    st.markdown('</div>', unsafe_allow_html=True)

# ── MAIN ──
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = {}

if not st.session_state.logged_in:
    pagina_login()
else:
    nav = sidebar()
    if nav == "Panel principal":
        panel_principal()
    elif nav == "Equipos":
        pagina_equipos()
    elif nav == "Configuracion remota":
        pagina_config()
    elif nav == "Nuevo equipo":
        pagina_nuevo_equipo()
