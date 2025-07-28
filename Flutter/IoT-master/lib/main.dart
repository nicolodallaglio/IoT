import 'dart:async';
import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:url_launcher/url_launcher.dart';
import 'api_service.dart';
import 'calendar_screen.dart';
import 'event_sync_service.dart';
import 'google_calendar_service.dart';
import 'feedback_service.dart';
import 'mqtt_service.dart';


void main() {
  runApp(const MyApp());
}

class MyApp extends StatefulWidget {
  const MyApp({super.key});

  @override
  State<MyApp> createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> {
  final EventSyncService _syncService = EventSyncService();



  @override
  void initState() {
    super.initState();
    _syncService.startSync();
  }

  @override
  void dispose() {
    _syncService.stopSync();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Aula Migliore',
      navigatorKey: navigatorKey, // 👈 IMPORTANTE
      theme: ThemeData(
        primarySwatch: Colors.blue,
      ),
      home: const AulaPage(),
    );
  }
}

class AulaPage extends StatefulWidget {
  const AulaPage({super.key});

  @override
  _AulaPageState createState() => _AulaPageState();
}

class _AulaPageState extends State<AulaPage> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;
  final ApiService _apiService = ApiService();
  final MqttService _mqttService = MqttService();
  bool _loading = true;

  Timer? _refreshTimer;

  double _buttonOffset = 0.0;
  final double _maxSwipeDistance = 200.0;
  bool _isDropdownVisible = false;
  List<dynamic> _otherAule = [];
  List<dynamic> _tutteLeAule = [];

  String _selectedFilter = 'all'; // valori: all, studio, lavoro


  @override
  void initState() {
    super.initState();

    _controller = AnimationController(
      duration: const Duration(milliseconds: 1000),
      vsync: this,
    )..repeat(reverse: true);

    _animation = Tween<double>(begin: -10, end: 10)
        .animate(CurvedAnimation(parent: _controller, curve: Curves.easeInOut));

    _apiService.sendUserLocation();

    _apiService.fetchAule().then((aule) {
      setState(() {
        _tutteLeAule = aule;
        _loading = false;
      });
    });

    _refreshTimer = Timer.periodic(const Duration(seconds: 60), (timer) {
      _apiService.fetchAule().then((aule) {
        if (mounted) {
          setState(() {
            _tutteLeAule = aule;
          });
        }
      });
    });

    _mqttService.connectAndListen((message) {
      if (mounted) {
        _showMqttNotification(context, message);
      }
    });
  }

  void _showMqttNotification(BuildContext context, String message) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Notifica'),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Chiudi'),
          ),
        ],
      ),
    );
  }



  @override
  void dispose() {
    _controller.dispose();
    _refreshTimer?.cancel();
    super.dispose();
  }

  List<dynamic> _sortAuleByRating(List<dynamic> aule) {
    List<dynamic> sortedAule = List.from(aule);
    sortedAule.sort((a, b) => b['rating'].compareTo(a['rating']));
    return sortedAule;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Trova la tua aula'),
        actions: [
          DropdownButtonHideUnderline(
            child: DropdownButton<String>(
              value: _selectedFilter,
              dropdownColor: Colors.white,
              icon: const Icon(Icons.arrow_drop_down, color: Colors.white),
              items: const [
                DropdownMenuItem(value: 'all', child: Text('Vedi tutte')),
                DropdownMenuItem(value: 'studio', child: Text('Aule studio')),
                DropdownMenuItem(value: 'lavoro', child: Text('Aule lavoro')),
              ],
              onChanged: (value) {
                if (value != null) {
                  setState(() {
                    _selectedFilter = value;
                    // 👇 niente fetch, i dati sono già in cache
                  });
                }
              },



              style: const TextStyle(color: Colors.black),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.calendar_today),
            onPressed: () async {
              final calendarService = GoogleCalendarService();
              try {
                await calendarService.signOut();
                await calendarService.getTodayEvents();

                if (!context.mounted) return;
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => CalendarScreen()),
                );
              } catch (e) {
                if (!context.mounted) return;
                showDialog(
                  context: context,
                  builder: (context) => AlertDialog(
                    title: const Text("Errore"),
                    content: Text("Errore nel login: \$e"),
                    actions: [
                      TextButton(
                        onPressed: () => Navigator.pop(context),
                        child: const Text("Ok"),
                      ),
                    ],
                  ),
                );
              }
            },
          ),
        ],
      ),
      body: Stack(
        children: [
          Positioned.fill(
            child: Image.network(
              'https://www.italieonline.eu/img/t1100h0/blogimg/leto/emilia-romagna/modena-uvod.jpg',
              fit: BoxFit.cover,
            ),
          ),
          Positioned.fill(
            child: Container(color: Colors.black.withOpacity(0.5)),
          ),
          _loading
              ? const Center(child: CircularProgressIndicator())
              : _buildFilteredContent()



        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          setState(() {
            _isDropdownVisible = !_isDropdownVisible;
          });
        },
        backgroundColor: Colors.transparent,
        elevation: 0,
        child: Container(
          decoration: BoxDecoration(
            color: Colors.black.withOpacity(0.5),
            borderRadius: BorderRadius.circular(100),
          ),
          padding: const EdgeInsets.all(10.0),
          child: const Icon(
            Icons.expand_more,
            color: Colors.white,
          ),
        ),
      ),
      bottomNavigationBar: _isDropdownVisible ? _buildDropdownMenu() : null,
    );
  }
  Widget _buildFilteredContent() {
    final filteredAule = _selectedFilter == 'all'
        ? _tutteLeAule
        : _tutteLeAule.where((a) => a['type'] == _selectedFilter).toList();

    if (filteredAule.isEmpty) {
      _otherAule = [];
      return const Center(
        child: Text('Nessuna aula trovata con questo filtro', style: TextStyle(color: Colors.white)),
      );
    }

    final sorted = _sortAuleByRating(filteredAule);
    final topAula = sorted.first;
    _otherAule = sorted.length > 1 ? sorted.sublist(1) : [];

    return _buildAulaList(topAula);
  }

  Widget _buildAulaList(dynamic topAula) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          GestureDetector(
            onHorizontalDragUpdate: (details) {
              setState(() {
                if (details.delta.dx > 0) {
                  _buttonOffset += details.delta.dx;
                  if (_buttonOffset > _maxSwipeDistance) {
                    _buttonOffset = _maxSwipeDistance;
                  }
                }
              });
            },
            onHorizontalDragEnd: (details) {
              if (_buttonOffset > 100) {
                _showBookingDialog(topAula);
                setState(() {
                  _buttonOffset = 0.0;
                });
              } else {
                setState(() {
                  _buttonOffset = 0.0;
                });
              }
            },
            child: Container(
              margin: EdgeInsets.only(left: _buttonOffset),
              child: ElevatedButton(
                onPressed: () => _showAulaDetails(context, topAula),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.transparent,
                  foregroundColor: Colors.white,
                  elevation: 0,
                  side: const BorderSide(color: Colors.white, width: 2),
                  minimumSize: const Size(200, 80),
                  textStyle: const TextStyle(fontSize: 25, shadows: [
                    Shadow(offset: Offset(1, 1), color: Colors.black, blurRadius: 2),
                  ]),
                ),
                child: Text(
                  '${topAula['name']}\nCosto: ${topAula['price']}€',
                ),
              ),
            ),
          ),
          const SizedBox(height: 20),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              _buildAnimatedArrow(),
              const SizedBox(width: 20),
              _buildAnimatedArrow(),
              const SizedBox(width: 20),
              _buildAnimatedArrow(),
            ],
          ),
          const SizedBox(height: 20),
          const Text('Fai swipe per prenotare', style: TextStyle(fontSize: 18, color: Colors.white)),
        ],
      ),
    );
  }

  void _showBookingDialog(dynamic room) {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Conferma Prenotazione'),
          content: const Text('Vuoi confermare la prenotazione dell\'aula?'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('No'),
            ),
            TextButton(
              onPressed: () {
                Navigator.of(context).pop();
                _showConfirmedDialog(room);
              },
              child: const Text('Sì'),
            ),
          ],
        );
      },
    );
  }

  void _showConfirmedDialog(dynamic room) {
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Prenotazione'),
          content: const Text('Aula prenotata!'),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(context).pop();
                FeedbackService().checkForFeedback(context, room); // <-- QUI
              },
              child: const Text('Chiudi'),
            ),
          ],
        );
      },
    );
  }


  Widget _buildAnimatedArrow() {
    return AnimatedBuilder(
      animation: _animation,
      builder: (context, child) {
        return Transform.translate(
          offset: Offset(_animation.value, 0),
          child: const Icon(Icons.arrow_right, size: 50, color: Colors.blue),
        );
      },
    );
  }

  Widget _buildDropdownMenu() {
    if (_otherAule.isEmpty) {
      return const SizedBox.shrink();
    }

    return Container(
      color: Colors.white.withOpacity(0.8),
      height: MediaQuery.of(context).size.height * 0.4,
      child: Column(
        children: [
          const Padding(
            padding: EdgeInsets.all(8.0),
            child: Text('Altre aule', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          ),
          Expanded(
            child: ListView.builder(
              itemCount: _otherAule.length,
              itemBuilder: (context, index) {
                final aula = _otherAule[index];
                double buttonOffset = 0.0;

                return StatefulBuilder(
                  builder: (context, setState) {
                    return GestureDetector(
                      onHorizontalDragUpdate: (details) {
                        setState(() {
                          buttonOffset += details.delta.dx;
                          if (buttonOffset > _maxSwipeDistance) {
                            buttonOffset = _maxSwipeDistance;
                          } else if (buttonOffset < 0) {
                            buttonOffset = 0.0;
                          }
                        });
                      },
                      onHorizontalDragEnd: (details) {
                        if (buttonOffset > 100) {
                          _showBookingDialog(aula);
                          setState(() {
                            buttonOffset = 0.0;
                          });
                        } else {
                          setState(() {
                            buttonOffset = 0.0;
                          });
                        }
                      },
                      child: Stack(
                        children: [
                          Positioned.fill(
                            child: Align(
                              alignment: Alignment.centerLeft,
                              child: Container(
                                width: buttonOffset,
                                color: Colors.green,
                              ),
                            ),
                          ),
                          Transform.translate(
                            offset: Offset(buttonOffset, 0),
                            child: ListTile(
                              title: Text(
                                aula['type'] == 'lavoro'
                                    ? '${aula['name']} - ${aula['price'].toStringAsFixed(2)}€'
                                    : aula['name'],
                              ),
                              onTap: () => _showAulaDetails(context, aula),
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  void _showAulaDetails(BuildContext context, dynamic aula) {
    final latitude = aula['latitudine'] as double?;
    final longitude = aula['longitudine'] as double?;

    if (latitude == null || longitude == null) {
      showDialog(
        context: context,
        builder: (BuildContext context) {
          return AlertDialog(
            title: const Text('Errore'),
            content: const Text('Posizione non disponibile per questa aula.'),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Chiudi'),
              ),
            ],
          );
        },
      );
      return;
    }

    final LatLng aulaPosition = LatLng(latitude, longitude);

    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: Text('Dettagli Aula: ${aula['name']}'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Nome Aula: ${aula['name']}'),
              Text('Costo: ${aula['price']}€'),
              const SizedBox(height: 10),
              Text('--- Dati Sensori ---'),
              Text('Luce: ${_valutaLuce(aula['light'])}'),
              Text('Rumore: ${_valutaRumore(aula['sound'])}'),
              Text('Temperatura: ${aula['temperature']}°C'),
              Text('Umidità: ${aula['humidity']}%'),
              Text('CO2: ${_valutaCO2(aula['co2'])}'),
              const SizedBox(height: 10),
              SizedBox(
                height: 150,
                child: GoogleMap(
                  initialCameraPosition: CameraPosition(
                    target: aulaPosition,
                    zoom: 15,
                  ),
                  markers: {
                    Marker(
                      markerId: MarkerId(aula['name']),
                      position: aulaPosition,
                      infoWindow: InfoWindow(title: aula['name']),
                    ),
                  },
                  onTap: (_) => _launchMaps(aulaPosition),
                  myLocationEnabled: false,
                  zoomControlsEnabled: false,
                ),
              ),
              const SizedBox(height: 10),
              const Center(
                child: Text(
                  "Tocca la mappa per indicazioni",
                  style: TextStyle(fontSize: 12, color: Colors.blueGrey),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Chiudi'),
            ),
          ],
        );
      },
    );
  }
  String _valutaCO2(dynamic valore) {
    final co2 = double.tryParse(valore.toString()) ?? 0;
    if (co2 < 400) return "BASSA";
    if (co2 < 800) return "OK";
    return "ALTA";
  }

  String _valutaRumore(dynamic valore) {
    final sound = double.tryParse(valore.toString()) ?? 0;
    if (sound < 30) return "BASSA";
    if (sound < 50) return "OK";
    return "ALTA";
  }

  String _valutaLuce(dynamic valore) {
    final light = double.tryParse(valore.toString()) ?? 0;
    if (light < 350) return "BASSA";
    if (light <= 700) return "OK";
    return "ALTA";
  }


  Future<void> _launchMaps(LatLng position) async {
    final googleMapsUrl = "https://www.google.com/maps/search/?api=1&query=\${position.latitude},\${position.longitude}";
    if (await canLaunch(googleMapsUrl)) {
      await launch(googleMapsUrl);
    } else {
      throw 'Non è possibile aprire Google Maps';
    }
  }
}
