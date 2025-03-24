import os
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split, GridSearchCV
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

# Modello di classificazione
param_grid = {
    'max_depth': [3, 5, 7, 10],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 5]
}
grid_search = GridSearchCV(DecisionTreeClassifier(random_state=42), param_grid, cv=5, n_jobs=-1, scoring='accuracy')
grid_search.fit(X_train_scaled, y_train)

# Miglior modello ottenuto
model = grid_search.best_estimator_

# Valutazione del modello
y_pred = model.predict(X_test_scaled)
accuracy = accuracy_score(y_test, y_pred)
report = classification_report(y_test, y_pred)

print(f"Accuratezza: {accuracy:.4f}")
print(f"Report di Classificazione:\n{report}")

# Salvataggio del modello e dello scaler
joblib.dump(model, 'occupancy_model.pkl')
joblib.dump(scaler, 'scaler.pkl')
print("✅ Modello e scaler salvati con successo!")
