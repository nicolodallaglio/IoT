import 'package:flutter/material.dart';
import 'google_calendar_service.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class CalendarScreen extends StatefulWidget {
  final bool forceAccountSelection;
  const CalendarScreen({super.key, this.forceAccountSelection = false});

  @override
  State<CalendarScreen> createState() => _CalendarScreenState();
}

class _CalendarScreenState extends State<CalendarScreen> {
  late GoogleCalendarService _calendarService;
  late Future<List<dynamic>> _eventsFuture;

  @override
  void initState() {
    super.initState();
    _calendarService = GoogleCalendarService(forceAccountSelection: widget.forceAccountSelection);
    _eventsFuture = _fetchAndSendEvents(); // ⬅️ Al primo build invia
  }

  Future<List<dynamic>> _fetchAndSendEvents() async {
    final events = await _calendarService.getTodayEvents();

    if (events.isEmpty) {
      debugPrint("Nessun evento da inviare: lista vuota.");
      return events;
    }

    final user = _calendarService.currentUser;
    final fullName = user?.displayName?.split(' ') ?? ["Nome", "Cognome"];
    final name = fullName.first;
    final surname = fullName.length > 1 ? fullName.sublist(1).join(" ") : "";

    final payload = {
      "name": name,
      "surname": surname,
      "eventi": events.map((e) {
        return {
          "titolo": e.summary ?? "Senza titolo",
          "luogo": e.location ?? "Non specificato",
          "inizio": e.start?.dateTime?.toUtc().toIso8601String(),
          "fine": e.end?.dateTime?.toUtc().toIso8601String(),
          "latitudine": 44.647,
          "longitudine": 10.925,
        };
      }).toList(),
    };

    print("📤 Payload da inviare: ${json.encode(payload)}");

    try {
      final response = await http.post(
        Uri.parse("http://smartrooms.ddns.net:8000/api/eventi-utente/"),
        headers: {"Content-Type": "application/json"},
        body: json.encode(payload),
      );

      if (response.statusCode == 200) {
        debugPrint("✅ Eventi inviati con successo");
      } else {
        debugPrint("❌ Errore dal server: ${response.body}");
      }
    } catch (e) {
      debugPrint("❌ Errore durante l'invio: $e");
    }

    return events;
  }


  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Eventi di oggi'),
        backgroundColor: Colors.blue,
      ),
      body: FutureBuilder(
        future: _eventsFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return Center(child: Text('Errore: \${snapshot.error}'));
          }

          final events = snapshot.data as List?;
          if (events == null || events.isEmpty) {
            return const Center(child: Text('Nessun evento trovato.'));
          }

          return ListView.builder(
            itemCount: events.length,
            itemBuilder: (context, index) {
              final e = events[index];
              final title = e.summary ?? 'Senza titolo';
              final time = e.start?.dateTime?.toLocal().toString() ?? 'Orario non disponibile';

              return ListTile(
                title: Text(title),
                subtitle: Text(time),
                leading: const Icon(Icons.event),
              );
            },
          );
        },
      ),
    );
  }
}
