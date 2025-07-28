import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:geolocator/geolocator.dart';
import 'package:google_sign_in/google_sign_in.dart'; // 👈 Import per ottenere l'utente

class ApiService {
  final String baseUrl = "http://smartrooms.ddns.net:8000/api/migliori-stanze/?";
  final String locationUrl = "http://smartrooms.ddns.net:8000/api/location/?";



  // Metodo per ottenere i dati delle aule dal server
  Future<List<dynamic>> fetchAule() async {
    final response = await http.get(Uri.parse(baseUrl));

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);

      print('Risposta dal server: ${response.body}');
      print('Numero di stanze recuperate: ${data['rooms'].length}');

      return data['rooms'];
    } else {
      throw Exception('Errore nel caricamento delle aule');
    }
  }

  // Metodo per ottenere la posizione dell'utente e inviarla al server
  Future<void> sendUserLocation() async {
    bool serviceEnabled;
    LocationPermission permission;

    // Controlla se i servizi di localizzazione sono abilitati
    serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      print("Servizi di localizzazione disabilitati.");
      return;
    }

    // Richiede i permessi di localizzazione
    permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) {
        print("Permessi di localizzazione negati.");
        return;
      }
    }

    if (permission == LocationPermission.deniedForever) {
      print("Permessi di localizzazione negati permanentemente.");
      return;
    }

    // Ottiene la posizione attuale
    Position position = await Geolocator.getCurrentPosition();
    final latitude = position.latitude;
    final longitude = position.longitude;

    print("Latitudine: $latitude, Longitudine: $longitude");

    // 📛 Ottieni nome e cognome dall'account Google
    final user = GoogleSignIn().currentUser;
    final fullName = user?.displayName?.split(' ') ?? ["Nome", "Cognome"];
    final name = fullName.first;
    final surname = fullName.length > 1 ? fullName.sublist(1).join(" ") : "";

    // Invia la posizione e i dati utente al server
    try {
      final response = await http.post(
        Uri.parse(locationUrl),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "name": name,
          "surname": surname,
          "latitudine": latitude,
          "longitudine": longitude,
        }),
      );

      if (response.statusCode == 200) {
        print("📍 Posizione e dati utente inviati con successo.");
      } else {
        print("❌ Errore nell'invio della posizione: ${response.statusCode}");
      }
    } catch (e) {
      print("❌ Errore di rete: $e");
    }
  }
}
