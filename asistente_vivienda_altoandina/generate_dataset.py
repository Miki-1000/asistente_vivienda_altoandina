import os
import pandas as pd
import re

# Configuración de directorio y atributos
DIR_PATH = 'esquemas'
OUTPUT_CSV = 'prototipos_altoandinos.csv'

# Espacios adicionales a considerar
EXTRAS_POSIBLES = ['fogón', 'huerto', 'establo', 'corral', 'chiquero']

# Función para parsear nombre de archivo según convención:
# plano_[FORMA]_[MEDIDA]m_[N°DORM]dorm_[PASILLO/EXCLUSA]_[TIPO_BAÑO]_[UBICACIÓN_COCINA]_[UBICACIÓN_BLOQUE_DORM]_[UBICACIÓN_DEPÓSITO]_[EXTRAS].png

def parse_filename(fname):
    name = fname.replace('.png', '')
    parts = name.split('_')
    # Desempaquetado
    # ['plano', forma, medida, dorm, paso, bano, coc, bloq, depo, extras]
    try:
        _, forma, medida_raw, dorm_raw, paso, bano, ubic_coc, ubic_bloq, ubic_depo, extras_raw = parts
    except ValueError:
        # Si no hay extras, la última parte podría faltar
        extras_raw = 'ninguno'
        _, forma, medida_raw, dorm_raw, paso, bano, ubic_coc, ubic_bloq, ubic_depo = parts

    # Medidas: e.g. '13x15m'
    m = re.match(r"([0-9]+(?:\.[0-9]+)?)x([0-9]+(?:\.[0-9]+)?)m", medida_raw)
    ancho = float(m.group(1)) if m else None
    profundidad = float(m.group(2)) if m else None

    # Dormitorios
    dormitorios = int(dorm_raw.replace('dorm', ''))

    # Extras booleanos
    extras_list = extras_raw.split('-') if extras_raw and extras_raw != 'ninguno' else []
    extras_dict = {e: (e in extras_list) for e in EXTRAS_POSIBLES}

    return {
        'id_plano': name,
        'forma': forma if forma in ['L','U'] else None,
        'ancho_m': ancho,
        'profundidad_m': profundidad,
        'habitaciones': dormitorios,
        'tipo_paso': paso,
        'tipo_bano': bano,
        'ubicacion_cocina': ubic_coc,
        'ubicacion_bloque_dorm': ubic_bloq,
        'ubicacion_deposito': ubic_depo,
        **extras_dict
    }

# Construcción de registros
registros = []
for fname in os.listdir(DIR_PATH):
    if fname.lower().endswith('.png') and fname.startswith('plano_'):
        data = parse_filename(fname)
        registros.append(data)

# DataFrame y salida
df = pd.DataFrame(registros)
# Ordenar columnas de manera lógica
cols = [
    'id_plano','forma','ancho_m','profundidad_m','habitaciones',
    'tipo_paso','tipo_bano','ubicacion_cocina','ubicacion_bloque_dorm','ubicacion_deposito'
] + EXTRAS_POSIBLES

# Asegurar que todas las columnas existen
for col in cols:
    if col not in df.columns:
        df[col] = None

df = df[cols]
df.to_csv(OUTPUT_CSV, index=False)
print(f"Dataset generado en: {OUTPUT_CSV} con {len(df)} registros.")
