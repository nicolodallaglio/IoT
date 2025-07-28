import 'package:mqtt_client/mqtt_client.dart';
import 'package:mqtt_client/mqtt_server_client.dart';

class MqttService {
  late MqttServerClient client;
  final String username = 'nicodalla99';
  final String key = "aio_Nmgf31z2Sd530yAMLfe6o8Xs31gm"; // chiave AIO
  final String topic = 'nicodalla99/feeds/utente-notifiche'; // topic unico per notifiche

  Future<void> connectAndListen(Function(String message) onMessageReceived) async {
    client = MqttServerClient.withPort(
      'io.adafruit.com',
      'flutterClient_${DateTime.now().millisecondsSinceEpoch}', // ID unico casuale
      1883,
    );

    client.logging(on: false);
    client.keepAlivePeriod = 60;
    client.onDisconnected = () => print("🔌 Disconnesso da MQTT");
    client.onConnected = () => print("✅ Connesso a MQTT!");
    client.secure = false;
    client.setProtocolV311();

    final connMess = MqttConnectMessage()
        .withClientIdentifier('flutter_client')
        .authenticateAs(username, key)
        .startClean();

    client.connectionMessage = connMess;

    try {
      await client.connect();
    } catch (e) {
      print('❌ Errore connessione MQTT: $e');
      client.disconnect();
      return;
    }

    client.subscribe(topic, MqttQos.atMostOnce);

    client.updates!.listen((List<MqttReceivedMessage<MqttMessage>> messages) {
      final recMess = messages[0].payload as MqttPublishMessage;
      final pt = MqttPublishPayload.bytesToStringAsString(recMess.payload.message);
      print("🔔 Notifica ricevuta: $pt");
      onMessageReceived(pt);
    });
  }

  void disconnect() {
    client.disconnect();
  }
}
