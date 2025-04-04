import os 
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import classification_report, accuracy_score

# Carica il dataset
file = r'C:\Users\Nicolò\Documents\IoT2025\dataset.csv'
dataset = pd.read_csv(file)

# Pre-elabora il dataset
X = dataset[['Temperature', 'Humidity', 'Light_scaled', 'CO2_scaled', 'Sound', 'Room_Size', 'People']]
y = dataset['BestRoom']

# Suddividi il dataset in set di addestramento e test
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

# Normalizzazione
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Modello di classificazione con Pruning
model = DecisionTreeClassifier(
    random_state=42,
    max_depth=7,
    min_samples_split=5,
    min_samples_leaf=2,
    ccp_alpha=0.02
)

# Addestramento del modello
model.fit(X_train_scaled, y_train)

# Predizioni su train e test
y_train_pred = model.predict(X_train_scaled)
y_test_pred = model.predict(X_test_scaled)

# Accuratezza su train e test
train_accuracy = accuracy_score(y_train, y_train_pred)
test_accuracy = accuracy_score(y_test, y_test_pred)

# Report di classificazione su train e test
train_report = classification_report(y_train, y_train_pred)
test_report = classification_report(y_test, y_test_pred)

print(f"🔍 METRICHE TRAINING:")
print(f"Accuratezza (Train): {train_accuracy:.4f}")
print(f"Report di Classificazione (Train):\n{train_report}")

print(f"🔍 METRICHE TEST:")
print(f"Accuratezza (Test): {test_accuracy:.4f}")
print(f"Report di Classificazione (Test):\n{test_report}")

# Salvataggio del modello e dello scaler
joblib.dump(model, 'occupancy_model.pkl')
joblib.dump(scaler, 'scaler.pkl')
print("✅ Modello e scaler salvati con successo!")
