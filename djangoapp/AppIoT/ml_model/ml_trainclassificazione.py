import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, classification_report

# Carica il dataset
file_path = r'C:\Users\Nicolò\Documents\IoT2025\dataset.csv'
dataset = pd.read_csv(file_path)

# Feature e target
X = dataset[['Temperature', 'Humidity', 'Light_scaled', 'CO2_scaled', 'Sound', 'Room_Size', 'People']]
y = dataset['BestRoom']

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42, stratify=y
)

# Standardizzazione
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Modello molto semplice (forte underfitting)
model = DecisionTreeClassifier(
    random_state=42,
    max_depth=1,             # solo una decisione
    min_samples_split=50,    # evita split frequenti
    min_samples_leaf=25,     # ogni foglia ha molti campioni
    ccp_alpha=0.2            # pruning aggressivo
)

# Addestramento
model.fit(X_train_scaled, y_train)

# Predizioni e valutazione
y_train_pred = model.predict(X_train_scaled)
y_test_pred = model.predict(X_test_scaled)

print("Accuracy TRAIN:", accuracy_score(y_train, y_train_pred))
print("Accuracy TEST :", accuracy_score(y_test, y_test_pred))
print("\nClassification Report (TEST):")
print(classification_report(y_test, y_test_pred))

# Salvataggio
joblib.dump(model, "occupancy_model_very_underfit.pkl")
joblib.dump(scaler, "scaler.pkl")
