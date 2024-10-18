import os
import pandas as pd
import joblib
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
from sklearn.tree import DecisionTreeClassifier
from django.conf import settings

def train_model(file):
    # Carica il dataset da file
    dataset = pd.read_csv(file)

    # Pre-elabora il dataset
    X = dataset[['Temperature', 'Humidity', 'Light_scaled', 'CO2_scaled', 'Sound', 'Room_Size', 'People']]
    y = dataset['BestRoom']

    # Suddividi il dataset in set di addestramento e test
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

    # Normalizza le feature
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Imposta i parametri per GridSearchCV
    param_grid = {
        'max_depth': [3, 5, 7, 10],
        'min_samples_split': [2, 5, 10],
        'min_samples_leaf': [1, 2, 5]
    }

    # Esegui Grid Search per il Decision Tree
    grid_search = GridSearchCV(DecisionTreeClassifier(random_state=42), param_grid, cv=5, n_jobs=-1, scoring='accuracy')
    grid_search.fit(X_train_scaled, y_train)

    # Ottieni il miglior modello
    model = grid_search.best_estimator_

    # Valutazione tramite cross-validation
    cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5)

    # Addestra il modello
    model.fit(X_train_scaled, y_train)

    # Fai predizioni sul set di test
    y_pred = model.predict(X_test_scaled)

    # Calcola l'accuratezza e il report di classificazione
    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred)

    # Salva il modello addestrato
    model_path = os.path.join(settings.BASE_DIR, 'AppIoT', 'ml_model', 'occupancy_model.pkl')
    joblib.dump(model, model_path)

    return {
        "accuracy_train": np.mean(cv_scores),
        "accuracy_test": accuracy,
        "classification_report": report
    }

def predict_and_sort_rooms(input_data):
    # Carica il modello salvato
    model_path = os.path.join(settings.BASE_DIR, 'AppIoT', 'ml_model', 'occupancy_model.pkl')
    model = joblib.load(model_path)

    # Normalizza i dati di input
    scaler = StandardScaler()
    input_data_scaled = scaler.fit_transform(input_data)

    # Prevedi le probabilità e le classi
    probabilities = model.predict_proba(input_data_scaled)[:, 1]
    predicted_classes = model.predict(input_data_scaled)

    # Aggiungi le probabilità e le classi previste al DataFrame
    input_data['probability'] = probabilities
    input_data['predicted_class'] = predicted_classes

    # Ordina le stanze in base alla probabilità, dalla più alta alla più bassa
    sorted_rooms = input_data.sort_values(by='probability', ascending=False)

    return sorted_rooms
