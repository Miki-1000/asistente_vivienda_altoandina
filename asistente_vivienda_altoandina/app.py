import os
import pickle
from io import BytesIO
import streamlit as st
import pandas as pd
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader

st.set_page_config(page_title="Asistente de Vivienda Altoandina", layout="wide")

BASE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(BASE, 'prototipos_altoandinos.csv')
SCALER = os.path.join(BASE, 'scaler_altoandino.pkl')
KNN = os.path.join(BASE, 'knn_altoandino.pkl')
ENC = os.path.join(BASE, 'encoder_forma.pkl')
ESQ_DIR = os.path.join(BASE, 'esquemas')
ISO_F = os.path.join(BASE, 'isometrico', 'frente')
ISO_B = os.path.join(BASE, 'isometrico', 'atras')

@st.cache_resource
def load_artifacts():
    df = pd.read_csv(CSV)
    scaler = pickle.load(open(SCALER, 'rb'))
    knn = pickle.load(open(KNN, 'rb'))
    enc = pickle.load(open(ENC, 'rb'))
    return df, scaler, knn, enc

df_protos, scaler, knn, enc = load_artifacts()

# TÍTULO
st.title("🏡 Asistente de Vivienda Altoandina")
st.markdown("¡Hola! Te ayudaré a visualizar el esquema ideal para tu vivienda.\nPor favor, completa el formulario para mostrarte un plano funcional de vivienda junto con vistas isométricas que te ayuden a visualizar mejor tu vivienda ideal.")

# DATOS PERSONALES
with st.expander("🧾 Datos del solicitante (opcional)", expanded=False):
    nombre_persona = st.text_input("👤 Nombre de la persona")
    edad_persona = st.number_input("🎂 Edad", min_value=1, max_value=120, step=1)

# INPUTS
def sidebar_inputs():
    st.sidebar.header("Requisitos de vivienda")
    forma_pref = st.sidebar.selectbox("🏠 Preferencia de forma (opcional)", ["ninguna", "L", "U"])
    col1, col2 = st.sidebar.columns(2)
    ancho = col1.number_input("📐 Ancho (m)", 4.0, 30.0, 15.0, 0.5)
    prof = col2.number_input("📏 Fondo (m)", 4.0, 30.0, 15.0, 0.5)
    dorms = st.sidebar.slider("Número de dormitorios", 2, 4, 2)
    bano = st.sidebar.radio("Tipo de saneamiento", ["letrina", "biodigestor"])
    extras = st.sidebar.multiselect("🌱 Espacios adicionales", ['fogón', 'huerto', 'establo', 'corral', 'chiquero'])
    opciones_avanzadas = st.sidebar.checkbox("🔧 Mostrar opciones avanzadas")

    advanced_inputs = {}
    if opciones_avanzadas:
        ubic_coc = st.sidebar.selectbox("Ubicación cocina", ["frente-izquierda", "frente-medio", "frente-derecha",
            "medio-izquierda", "medio-medio", "medio-derecha", "fondo-izquierda", "fondo-medio", "fondo-derecha"])
        ubic_bloq = st.sidebar.selectbox("Ubicación bloque dormitorios", ["frente-izquierda", "frente-medio", "frente-derecha",
            "medio-izquierda", "medio-medio", "medio-derecha", "fondo-izquierda", "fondo-medio", "fondo-derecha"])
        ubic_dep = st.sidebar.selectbox("Ubicación depósito", ["izquierda-frente", "izquierda-medio", "izquierda-fondo",
            "medio-frente", "medio-medio", "medio-fondo", "derecha-frente", "derecha-medio", "derecha-fondo"])
        acceso_dormitorios = st.sidebar.radio("🛋️ Acceso a los dormitorios", ["pasillo", "esclusa"])
        advanced_inputs.update({
            'ubic_coc': ubic_coc,
            'ubic_bloq': ubic_bloq,
            'ubic_dep': ubic_dep,
            'acceso_dormitorios': acceso_dormitorios
        })

    st.session_state.pop('calc', None)
    return {
        'forma_pref': forma_pref,
        'ancho': ancho, 'prof': prof,
        'dorms': dorms,
        'bano': bano,
        'extras': extras,
        'opciones_avanzadas': opciones_avanzadas,
        **advanced_inputs
    }

inputs = sidebar_inputs()
if st.button("Calcular esquema ✅"):
    st.session_state['calc'] = True

if not st.session_state.get("calc"):
    st.stop()

def dimension_score(u, p, w):
    d = abs(u - p)
    if d <= 0.5: return w
    elif d <= 1: return w * 0.8
    elif d <= 1.5: return w * 0.6
    elif d <= 2: return w * 0.3
    else: return 0

def score_proto(inp, proto):
    s = 0
    s += 25 if proto['habitaciones'] == inp['dorms'] else (12.5 if abs(proto['habitaciones'] - inp['dorms']) == 1 else 0)
    s += dimension_score(inp['ancho'], proto['ancho_m'], 7.5)
    s += dimension_score(inp['prof'], proto['profundidad_m'], 7.5)
    sol = set(inp['extras'])
    ofe = set([e for e in ['fogón', 'huerto', 'establo', 'corral', 'chiquero'] if proto.get(e)])
    s += max(0, 25 - 3 * (len(sol - ofe) + len(ofe - sol)))
    s += 15 if proto['tipo_bano'] == inp['bano'] else 0
    s += 10 if inp['forma_pref'] == 'ninguna' else (20 if proto['forma'] == inp['forma_pref'] else 0)

    if inp.get('opciones_avanzadas'):
        if proto.get('tipo_paso') == inp.get('acceso_dormitorios'): s += 5
        if proto.get('ubicacion_cocina') == inp.get('ubic_coc'): s += 3
        if proto.get('ubicacion_bloque_dorm') == inp.get('ubic_bloq'): s += 3
        if proto.get('ubicacion_deposito') == inp.get('ubic_dep'): s += 3
    return s

def mostrar():
    results = [(r['id_plano'], score_proto(inputs, r)) for _, r in df_protos.iterrows()]
    top3 = sorted(results, key=lambda x: x[1], reverse=True)[:3]

    # PDF buffer
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    pw, ph = letter

    # 🧾 Portada
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(pw / 2, 750, "Resumen personalizado de vivienda sugerida")
    c.setFont("Helvetica", 12)
    y = 710
    if nombre_persona:
        c.drawString(60, y, f"👤 Nombre: {nombre_persona}")
        y -= 20
    if edad_persona:
        c.drawString(60, y, f"🎂 Edad: {int(edad_persona)} años")
        y -= 20
    c.drawString(60, y, "Este informe contiene las mejores opciones de esquema de vivienda")
    y -= 15
    c.drawString(60, y, "calculadas en función de los requerimientos ingresados.")
    c.showPage()

    # Encabezado
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(pw / 2, 770, "PROPUESTAS SUGERIDAS PARA TU VIVIENDA")
    c.showPage()

    cols = st.columns(3)
    for idx, (pid, sc) in enumerate(top3):
        r = df_protos[df_protos['id_plano'] == pid].iloc[0]
        with cols[idx % 3]:
            st.subheader(f"Opción {idx+1} — {sc:.0f}%")
            st.progress(sc / 100)

            # Mostrar esquema 2D
            img2d = os.path.join(ESQ_DIR, pid + '.png')
            if os.path.exists(img2d):
                st.image(img2d, caption="Esquema 2D", use_container_width=True)

            # Vistas 3D
            with st.expander("Ver vistas 3D", expanded=False):
                for label, folder in [("Isométrico Frente", ISO_F), ("Isométrico Atrás", ISO_B)]:
                    path = os.path.join(folder, pid + '.png')
                    if os.path.exists(path):
                        st.caption(label)
                        st.image(path, use_container_width=True)

            # PUNTAJES
            hab = 25 if r['habitaciones'] == inputs['dorms'] else (12.5 if abs(r['habitaciones'] - inputs['dorms']) == 1 else 0)
            an = dimension_score(inputs['ancho'], r['ancho_m'], 7.5)
            pr = dimension_score(inputs['prof'], r['profundidad_m'], 7.5)
            sol = set(inputs['extras'])
            ofe = set([e for e in ['fogón', 'huerto', 'establo', 'corral', 'chiquero'] if r[e] == 1])
            esp = max(0, 25 - 3 * (len(sol - ofe) + len(ofe - sol)))
            san = 15 if r['tipo_bano'] == inputs['bano'] else 0
            forma = 10 if inputs['forma_pref'] == 'ninguna' else (20 if r['forma'] == inputs['forma_pref'] else 0)
            paso = coc = bloq = dep = 0
            if inputs.get('opciones_avanzadas'):
                paso = 5 if r.get('tipo_paso') == inputs.get('acceso_dormitorios') else 0
                coc = 3 if r.get('ubicacion_cocina') == inputs.get('ubic_coc') else 0
                bloq = 3 if r.get('ubicacion_bloque_dorm') == inputs.get('ubic_bloq') else 0
                dep = 3 if r.get('ubicacion_deposito') == inputs.get('ubic_dep') else 0
            total_pts = hab + an + pr + esp + san + forma + paso + coc + bloq + dep

            # Detalle pantalla
            with st.expander("Detalle de puntuación"):
                st.write(f"• 🛏️ Dormitorios: {hab} puntos")
                st.write(f"• 📐 Ancho: {an:.1f} puntos")
                st.write(f"• 📏 Profundidad: {pr:.1f} puntos")
                st.write(f"• 🌱 Espacios adicionales: {esp} puntos")
                st.write(f"• 🚰 Saneamiento: {san} puntos")
                st.write(f"• 🏠 Forma: {forma} puntos")
                if inputs.get('opciones_avanzadas'):
                    st.write(f"• 🚪 Acceso dormitorios: {paso} puntos")
                    st.write(f"• 👨‍🍳 Cocina: {coc} puntos")
                    st.write(f"• 🛏️ Bloque dormitorio: {bloq} puntos")
                    st.write(f"• 📦 Depósito: {dep} puntos")
                st.write(f"**Total: {total_pts:.1f} puntos / 100**")

        # PDF para esta propuesta
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(pw / 2, 770, f"OPCIÓN {idx+1}")
        y = 740
        for img_path in [os.path.join(ESQ_DIR, pid + '.png'), os.path.join(ISO_F, pid + '.png'), os.path.join(ISO_B, pid + '.png')]:
            if os.path.exists(img_path):
                img = Image.open(img_path)
                iw, ih = img.size
                scale = min(420 / iw, 180 / ih)
                w, h = iw * scale, ih * scale
                x = (pw - w) / 2
                if y - h < 150:
                    c.showPage()
                    y = 750
                c.drawImage(ImageReader(img), x, y - h, w, h)
                y -= h + 12

        # Puntos PDF
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, "Detalle de puntuación:")
        y -= 15
        c.setFont("Helvetica", 9)
        for linea in [
            f"• Dorm: {hab} | Ancho: {an:.1f} | Prof: {pr:.1f}",
            f"• Esp: {esp} | San: {san} | Forma: {forma}",
            f"• Acceso: {paso} | Coc: {coc} | Bloq: {bloq} | Dep: {dep}",
            f"→ TOTAL: {total_pts:.1f} / 100"
        ]:
            c.drawString(60, y, linea)
            y -= 12

        # ¿Qué falta?
        faltan = []
        if inputs["forma_pref"] == "ninguna":
            faltan.append("ℹ️ No seleccionaste forma preferida, aporta 10/20 puntos.")
        elif r["forma"] != inputs["forma_pref"]:
            faltan.append("❌ Forma no coincide con tu preferencia.")
        if r["habitaciones"] != inputs["dorms"]:
            faltan.append(f"❌ Dormitorios: pediste {inputs['dorms']}, plano tiene {r['habitaciones']}.")
        if abs(inputs['ancho'] - r['ancho_m']) > 0.5:
            faltan.append(f"❌ Ancho: pediste {inputs['ancho']}m, plano tiene {r['ancho_m']}m.")
        if abs(inputs['prof'] - r['profundidad_m']) > 0.5:
            faltan.append(f"❌ Profundidad: pediste {inputs['prof']}m, plano tiene {r['profundidad_m']}m.")
        if r['tipo_bano'] != inputs['bano']:
            faltan.append(f"❌ Saneamiento: pediste '{inputs['bano']}', plano tiene '{r['tipo_bano']}'.")
        if sol - ofe:
            faltan.append(f"❌ Faltan espacios: {', '.join(sol - ofe)}.")
        if ofe - sol:
            faltan.append(f"❌ Espacios no requeridos: {', '.join(ofe - sol)}.")
        if inputs.get('opciones_avanzadas'):
            if paso == 0: faltan.append("❌ Tipo de acceso no coincide.")
            if coc == 0: faltan.append("❌ Cocina mal ubicada.")
            if bloq == 0: faltan.append("❌ Bloque dormitorio no coincide.")
            if dep == 0: faltan.append("❌ Depósito no coincide.")
        if faltan:
            y -= 15
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, y, "¿Qué falta para llegar al 100%?")
            y -= 12
            c.setFont("Helvetica", 9)
            for f in faltan:
                if y < 60:
                    c.showPage()
                    y = 750
                c.drawString(60, y, f"• {f}")
                y -= 11
        c.showPage()

    # PDF listo
    c.save()
    buf.seek(0)
    st.download_button("📥 Descargar PDF", data=buf, file_name="resumen_vivienda.pdf", mime="application/pdf")

mostrar()
