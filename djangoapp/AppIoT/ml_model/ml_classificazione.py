import os
import pandas as pd
import joblib
from django.conf import settings

"""# Carica il modello e lo scaler all'avvio del server
MODEL_PATH = "C:/Users/Nicolò/Documents/IoT2025/IoT/occupancy_model.pkl"
SCALER_PATH = "C:/Users/Nicolò/Documents/IoT2025/IoT/scaler.pkl"""

# Percorsi dei file basati sulla directory del progetto Django
MODEL_PATH = os.path.join(settings.BASE_DIR, 'AppIoT', 'ml_model', 'occupancy_model.pkl')
SCALER_PATH = os.path.join(settings.BASE_DIR, 'AppIoT', 'ml_model', 'scaler.pkl')

# Caricamento del modello e dello scaler
try:
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    print("Debug: Modello e scaler caricati correttamente!")
except FileNotFoundError as e:
    print(f"Errore: {e}")

def predict_and_sort_rooms(input_data):
    # Verifica se il modello e lo scaler sono stati caricati correttamente
    if model is None or scaler is None:
        raise Exception("Modello o scaler non trovati!")

    # Normalizza i dati di input
    input_data_scaled = scaler.transform(input_data)

    # Predizione
    probabilities = model.predict_proba(input_data_scaled)[:, 1]
    predicted_classes = model.predict(input_data_scaled)

    # Aggiungi i risultati al DataFrame
    input_data['probability'] = probabilities
    input_data['predicted_class'] = predicted_classes

    # Ordina le stanze per probabilità decrescente
    sorted_rooms = input_data.sort_values(by='probability', ascending=False)

    return sorted_rooms