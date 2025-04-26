import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score

# Carica il dataset
file_path = r'C:\Users\Nicolò\Documents\IoT2025\dataset_con_prob_abs_val.csv'
df = pd.read_csv(file_path)

# Feature e target
X = df.drop(columns=["prob", "BestRoom"])  # Rimuovi 'prob' (target) e 'BestRoom' (se non serve)
y = df["prob"]  # Target: probabilità

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Standardizzazione
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Modello di regressione lineare
model = LinearRegression()
model.fit(X_train_scaled, y_train)

# Predizioni e valutazione
y_train_pred = model.predict(X_train_scaled)
y_test_pred = model.predict(X_test_scaled)

print("MSE TRAIN:", mean_squared_error(y_train, y_train_pred))
print("MSE TEST :", mean_squared_error(y_test, y_test_pred))
print("R^2 TRAIN:", r2_score(y_train, y_train_pred))
print("R^2 TEST :", r2_score(y_test, y_test_pred))

# Salvataggio del modello e dello scaler
joblib.dump(model, "regression_model.pkl")
joblib.dump(scaler, "scaler.pkl")
