import 'dart:async';
import 'dart:convert';
import 'package:googleapis/calendar/v3.dart' as calendar;
import 'package:google_sign_in/google_sign_in.dart';
import 'package:http/http.dart' as http;
import 'google_calendar_service.dart';

class EventSyncService {
  final GoogleCalendarService _calendarService = GoogleCalendarService();
  Timer? _timer;

  void startSync() {
    _fetchAndSend();
    _timer = Timer.periodic(const Duration(seconds: 60), (timer) {
      _fetchAndSend();
    });
  }

  void stopSync() {
    _timer?.cancel();
  }

  Future<void> _fetchAndSend() async {
    try {
      final fetchedEvents = await _calendarService.getTodayEvents();
      if (fetchedEvents.isEmpty) {
        print("Nessun evento da sincronizzare.");
        return;
      }


      final user = _calendarService.currentUser;
      final fullName = user?.displayName?.split(' ') ?? ["Nome", "Cognome"];
      final name = fullName.first;
      final surname = fullName.length > 1 ? fullName.sublist(1).join(" ") : "";

      final payload = {
        "name": name,
        "surname": surname,
        "eventi": fetchedEvents.map((e) {
          return {
            "titolo": e.summary ?? "Senza titolo",
            "luogo": e.location ?? "Luogo non disponibile",
            "inizio": e.start?.dateTime?.toIso8601String() ?? "",
            "fine": e.end?.dateTime?.toIso8601String() ?? "",
            "latitudine": 0.0,
            "longitudine": 0.0,
          };
        }).toList(),
      };

      // 👇 Aggiungi questo per il debug
      print("📤 Payload SYNC da inviare: ${jsonEncode(payload)}");

      final response = await http.post(
        Uri.parse("http://smartrooms.ddns.net:8000/api/eventi-utente/"),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode(payload),
      );

      if (response.statusCode == 200) {
        print("✅ Eventi inviati in background");
      } else {
        print("❌ Errore dal server: ${response.body}");
      }
    } catch (e) {
      print("❌ Errore durante la sincronizzazione eventi: $e");
    }

  }
}
