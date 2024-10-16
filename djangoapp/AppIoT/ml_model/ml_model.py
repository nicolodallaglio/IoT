import os
import pandas as pd
import joblib
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from django.conf import settings

def train_model(file):
    # Carica il dataset da file
    dataset = pd.read_csv(file)

    # Pre-elabora il dataset
    X = dataset.drop(columns=['Occupancy', 'date'])
    y = dataset['Occupancy']

    # Split dei dati
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, train_size=0.75, random_state=0, stratify=y)

    # Crea e addestra il modello
    model = DecisionTreeClassifier()
    model.fit(X_train, y_train)

    # Valuta il modello
    train_pred = model.predict(X_train)
    test_pred = model.predict(X_test)

    accuracy_train = accuracy_score(y_train, train_pred)
    accuracy_test = accuracy_score(y_test, test_pred)

    # Salva il modello addestrato
    model_path = os.path.join(settings.BASE_DIR, 'AppIoT', 'ml_model', 'occupancy_model.pkl')
    joblib.dump(model, model_path)

    return {
        "accuracy_train": accuracy_train,
        "accuracy_test": accuracy_test
    }

def predict_and_sort_rooms(input_data):
    # Carica il modello salvato
    model_path = os.path.join(settings.BASE_DIR, 'AppIoT', 'ml_model', 'occupancy_model.pkl')
    model = joblib.load(model_path)
    
    # Prevedi le probabilità e le classi
    probabilities = model.predict_proba(input_data)[:, 1]
    predicted_classes = model.predict(input_data)

    # Aggiungi le probabilità e le classi previste al DataFrame
    input_data['probability'] = probabilities
    input_data['predicted_class'] = predicted_classes

    # Ordina le stanze in base alla probabilità, dalla più alta alla più bassa
    sorted_rooms = input_data.sort_values(by='probability', ascending=False)

    return sorted_rooms

