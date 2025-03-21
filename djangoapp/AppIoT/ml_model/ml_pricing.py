#Ho fatto un piccolo algoritmo con random forest, c'è un errore medio di 40€ circa, 
# utilizzando il dataset che è composto di soli 100 elementi

#Caricare il dataset
file_path = "dataset_aule_modificato.csv"  # Modifica il percorso se necessario
df = pd.read_csv(file_path)

#Codificare la variabile categorica "Giorno della settimana"
label_encoder = LabelEncoder()
df["Giorno Codificato"] = label_encoder.fit_transform(df["Giorno della settimana"])

#Selezionare le feature e la variabile target
X = df[["Capienza Massima", "Evento nelle Vicinanze", "Giorno Codificato"]]
y = df["Prezzo (€)"]

#Suddividere il dataset in training (80%) e test (20%)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

#Addestrare il modello Random Forest Regressor
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

#Predire i prezzi sulle istanze di test
y_pred = model.predict(X_test)

#Valutare il modello
mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))

print(f"MAE: {mae:.2f}€")
print(f"RMSE: {rmse:.2f}€")

#Creare una nuova istanza da predire
nuova_aula = pd.DataFrame([[100, 1, label_encoder.transform(["Lunedì"])[0]]], 
                          columns=["Capienza Massima", "Evento nelle Vicinanze", "Giorno Codificato"])

#Fare la previsione
prezzo_predetto = model.predict(nuova_aula)[0]
prezzo_predetto_arrotondato = 5 * round(prezzo_predetto / 5)

print(f"Prezzo previsto: {prezzo_predetto_arrotondato:.2f}€")