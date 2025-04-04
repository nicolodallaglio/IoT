import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import LabelEncoder
import pickle
import os
import locale
from datetime import datetime

# Impostare la lingua italiana per i giorni della settimana
try:
    locale.setlocale(locale.LC_TIME, "it_IT.UTF-8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, "it_IT")
    except locale.Error:
        print("⚠️ Impossibile impostare il locale italiano. Verifica la configurazione locale del sistema.")

# Caricare il dataset
file_path = r'C:\Users\Nicolò\Documents\IoT2025\dataset_prezzo.csv'
df = pd.read_csv(file_path)

# Codificare la variabile categorica "Giorno della settimana"
label_encoder = LabelEncoder()
df["Giorno Codificato"] = label_encoder.fit_transform(df["Giorno della settimana"])

# Verificare i giorni codificati
print("Giorni codificati:", list(label_encoder.classes_))

# Selezionare le feature e la variabile target
X = df[["Capienza Massima", "Evento nelle Vicinanze", "Giorno Codificato"]]
y = df["price"]

# Suddividere il dataset in training (80%) e test (20%)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Addestrare il modello Random Forest Regressor
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Valutare il modello
y_pred = model.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
print(f"MAE: {mae:.2f}€")
print(f"RMSE: {rmse:.2f}€")

# Salvare il modello e l'encoder
model_path = os.path.join(os.path.dirname(__file__), "modello_prezzo.pkl")
with open(model_path, "wb") as file:
    pickle.dump((model, label_encoder), file)

print(f"✅ Modello e encoder salvati come '{model_path}'")

# Test locale: ottenere il giorno corrente in italiano
giorno_corrente = datetime.now().strftime("%A")
print(f"Giorno corrente (italiano): {giorno_corrente}")
