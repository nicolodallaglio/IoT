import 'package:google_sign_in/google_sign_in.dart';
import 'package:googleapis/calendar/v3.dart' as calendar;
import 'package:http/http.dart' as http;

/// Client HTTP personalizzato con header OAuth
class GoogleHttpClient extends http.BaseClient {
  final Map<String, String> _headers;
  final http.Client _client = http.Client();

  GoogleHttpClient(this._headers);

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) {
    return _client.send(request..headers.addAll(_headers));
  }

  @override
  void close() => _client.close();
}

class GoogleCalendarService {
  final bool forceAccountSelection;
  final GoogleSignIn _googleSignIn;
  GoogleSignInAccount? _account;

  GoogleCalendarService({this.forceAccountSelection = false})
      : _googleSignIn = GoogleSignIn(
    scopes: [calendar.CalendarApi.calendarReadonlyScope],
  );

  GoogleSignInAccount? get currentUser => _account;

  /// Effettua il login e recupera gli eventi di oggi da due calendari
  Future<List<calendar.Event>> getTodayEvents() async {
    if (forceAccountSelection) {
      await _googleSignIn.signOut();
    }

    _account = await _googleSignIn.signIn();
    if (_account == null) {
      throw Exception("Login annullato o fallito.");
    }

    final authHeaders = await _account!.authHeaders;
    final client = GoogleHttpClient(authHeaders);
    final calendarApi = calendar.CalendarApi(client);

    final now = DateTime.now().toUtc();
    final endOfDay = DateTime.utc(now.year, now.month, now.day + 1);

    // Eventi dal calendario principale
    final myEventsResponse = await calendarApi.events.list(
      'primary',
      timeMin: now,
      timeMax: endOfDay,
      singleEvents: true,
      orderBy: 'startTime',
    );

    // Eventi dal calendario condiviso (es: Nico)
    final nicoEventsResponse = await calendarApi.events.list(
      'dallaglionicol@gmail.com', // 🔁 Email o ID del calendario condiviso
      timeMin: now,
      timeMax: endOfDay,
      singleEvents: true,
      orderBy: 'startTime',
    );

    final allEvents = [
      ...(myEventsResponse.items ?? []),
      ...(nicoEventsResponse.items ?? []),
    ];

    allEvents.sort((a, b) {
      final aTime = a.start?.dateTime ?? DateTime.now();
      final bTime = b.start?.dateTime ?? DateTime.now();
      return aTime.compareTo(bTime);
    });

    return allEvents.cast<calendar.Event>();
  }

  Future<void> signOut() async {
    await _googleSignIn.signOut();
  }
}
