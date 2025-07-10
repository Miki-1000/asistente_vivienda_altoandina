import pandas as pd
import pickle
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import train_test_split

# 1. Carga del dataset actualizado
df = pd.read_csv("prototipos_altoandinos.csv")

# 2. Cálculo de variables derivadas
df["area_m2"] = df["ancho_m"] * df["profundidad_m"]
df["aspecto"] = df["ancho_m"] / df["profundidad_m"]

# 3. Definición de la clase de salida: forma (L, U, None)
le = LabelEncoder()
df["forma_encoded"] = le.fit_transform(df["forma"].fillna("None"))

# 4. One-hot encoding para variables categóricas
# tipo de paso (pasillo/exclusa)
df = pd.get_dummies(df, columns=["tipo_paso"], prefix="paso", drop_first=False)
# tipo de baño (letrina/biodigestor)
df = pd.get_dummies(df, columns=["tipo_bano"], prefix="bano", drop_first=False)
# ubicaciones
cols_ubic = ["ubicacion_cocina", "ubicacion_bloque_dorm", "ubicacion_deposito"]
df = pd.get_dummies(df, columns=cols_ubic, prefix=["cocina", "bloq_dorm", "deposito"], drop_first=False)

# 5. Espacios adicionales (ya booleanos): fogón, huerto, establo, corral, chiquero
extras = ['fogón', 'huerto', 'establo', 'corral', 'chiquero']
for col in extras:
    if col not in df.columns:
        df[col] = False

# 6. Selección de características y etiqueta
drop_cols = ["id_plano", "forma"]
feature_cols = [c for c in df.columns if c not in drop_cols + ["forma_encoded"]]
X = df[feature_cols]
y = df["forma_encoded"]

# 7. División entrenamiento/prueba
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

# 8. Entrenamiento del StandardScaler
scaler = StandardScaler().fit(X_train)
X_train_scaled = scaler.transform(X_train)

# 9. Entrenamiento del KNN (k=3)
knn = KNeighborsClassifier(n_neighbors=3).fit(X_train_scaled, y_train)

# 10. Guardar scaler, modelo y encoder de forma
with open("scaler_altoandino.pkl", "wb") as f:
    pickle.dump(scaler, f)
with open("knn_altoandino.pkl", "wb") as f:
    pickle.dump(knn, f)
with open("encoder_forma.pkl", "wb") as f:
    pickle.dump(le, f)

print("Actualización completada: scaler, knn y encoder guardados.")

