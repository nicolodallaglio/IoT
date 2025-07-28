import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:googleapis/calendar/v3.dart' as calendar;

/// Invia al server Django gli eventi recuperati da Google Calendar
Future<void> inviaEventiAlServer({
  required String nome,
  required String cognome,
  required List<calendar.Event> eventi,
}) async {
  final List<Map<String, dynamic>> eventiConvertiti = eventi.map((e) {
    final location = e.location ?? "";
    double? latitudine;
    double? longitudine;

    // Se la location è nel formato "lat, long", estrae i valori
    if (location.contains(',')) {
      final parts = location.split(',');
      if (parts.length == 2) {
        latitudine = double.tryParse(parts[0].trim());
        longitudine = double.tryParse(parts[1].trim());
      }
    }

    return {
      "titolo": e.summary ?? "Senza titolo",
      "luogo": location.isNotEmpty ? location : "Luogo non specificato",
      "inizio": e.start?.dateTime?.toIso8601String() ?? "",
      "fine": e.end?.dateTime?.toIso8601String() ?? "",
      "latitudine": latitudine,
      "longitudine": longitudine,
    };
  }).toList();

  final body = {
    "name": nome,
    "surname": cognome,
    "eventi": eventiConvertiti,
  };

  final url = Uri.parse('http://10.0.2.2:8000/api_eventi_utente/'); // Cambia con l’IP corretto se serve

  final response = await http.post(
    url,
    headers: {"Content-Type": "application/json"},
    body: jsonEncode(body),
  );

  if (response.statusCode == 200 || response.statusCode == 201) {
    print("✅ Eventi inviati al server Django.");
  } else {
    print("❌ Errore nell’invio degli eventi: ${response.statusCode}");
    print("Messaggio: ${response.body}");
  }
}
