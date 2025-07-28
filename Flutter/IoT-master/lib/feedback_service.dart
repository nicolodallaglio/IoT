import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:http/http.dart' as http;
import 'package:googleapis/calendar/v3.dart' as calendar;
import 'google_calendar_service.dart';
import 'package:flutter/widgets.dart';

final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();


class FeedbackService {
  final GoogleCalendarService _calendarService = GoogleCalendarService();
  Timer? _fallbackTimer;
  bool _hasShownFeedback = false;

  void resetFeedbackState() {
    _fallbackTimer?.cancel();
    _hasShownFeedback = false;
  }

  void checkForFeedback(BuildContext context, dynamic room) async {
    resetFeedbackState();
    try {
      final events = await _calendarService.getTodayEvents();
      final now = DateTime.now();

      final endingEvents = events.where((e) =>
      e.end?.dateTime != null &&
          e.end!.dateTime!.isBefore(now) &&
          e.end!.dateTime!.isAfter(now.subtract(const Duration(minutes: 1))));

      if (endingEvents.isNotEmpty) {
        _showFeedbackDialog(context, room);
      } else {
        // Se non c'è evento, fallback dopo 60 secondi (precisi)
        final fallbackContext = navigatorKey.currentContext;

        _fallbackTimer = Timer(const Duration(seconds: 60), () {
          if (!_hasShownFeedback && fallbackContext != null) {
            _showFeedbackDialog(fallbackContext, room);
          }
        });

      }
    } catch (e) {
      final fallbackContext = navigatorKey.currentContext;

      _fallbackTimer = Timer(const Duration(seconds: 60), () {
        if (!_hasShownFeedback && fallbackContext != null) {
          _showFeedbackDialog(fallbackContext, room);
        }
      });

    }
  }

  void _showFeedbackDialog(BuildContext context, dynamic room) {
    if (!Navigator.of(context).mounted) return; // ⛑ Protezione extra

    int voto = 3;
    String commento = "";

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (BuildContext dialogContext) {
        return AlertDialog(
          title: const Text('Lascia un feedback'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text("Quanto ti è piaciuta questa stanza?"),
              StatefulBuilder(
                builder: (context, setState) {
                  return DropdownButton<int>(
                    value: voto,
                    items: List.generate(5, (index) {
                      return DropdownMenuItem(
                        value: index + 1,
                        child: Text('${index + 1}'),
                      );
                    }),
                    onChanged: (val) {
                      if (val != null) {
                        setState(() {
                          voto = val;
                        });
                      }
                    },
                  );
                },
              ),
              TextField(
                decoration: const InputDecoration(labelText: "Commento"),
                onChanged: (val) => commento = val,
              )
            ],
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(dialogContext).pop();
              },
              child: const Text("Annulla"),
            ),
            TextButton(
              onPressed: () async {
                Navigator.of(dialogContext).pop();
                await _sendFeedback(room, voto, commento);
              },
              child: const Text("Invia"),
            ),
          ],
        );
      },
    );
  }


  Future<void> _sendFeedback(dynamic room, int voto, String commento) async {
    final user = GoogleSignIn().currentUser;
    final fullName = user?.displayName?.split(' ') ?? ["Nome", "Cognome"];
    final name = fullName.first;
    final surname = fullName.length > 1 ? fullName.sublist(1).join(" ") : "";

    final payload = {
      "name_stanza": room['name'],
      "latitudine": room['latitudine'],
      "longitudine": room['longitudine'],
      "voto": voto,
      "commento": commento,
      "name": name,
      "surname": surname,
    };

    try {
      final response = await http.post(
        Uri.parse("http://smartrooms.ddns.net:8000/api/feedback/"),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode(payload),
      );

      if (response.statusCode == 200) {
        print("✅ Feedback inviato con successo");
      } else {
        print("❌ Errore feedback: \${response.body}");
      }
    } catch (e) {
      print("❌ Errore invio feedback: \$e");
    }
  }
}
