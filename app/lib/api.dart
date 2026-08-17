import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';

/// Aegis backend client. Change [base] to your server address.
/// For Android emulator use http://10.0.2.2:8000
class AegisApi {
  static const String base = 'http://localhost:8000';
  static const String wsBase = 'ws://localhost:8000';

  Future<List<dynamic>> listUsers() async {
    final res = await http.get(Uri.parse('$base/users'));
    return jsonDecode(res.body) as List<dynamic>;
  }

  Future<void> upsertUser(
    String userId,
    String name,
    String email,
    String parentEmail,
  ) async {
    await http.post(
      Uri.parse('$base/users/upsert'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'google_id': userId,
        'name': name,
        'email': email,
        'parent_email': parentEmail,
      }),
    );
  }

  Future<void> heartbeat(String userId) async {
    try {
      await http.post(Uri.parse('$base/users/heartbeat?user_id=$userId'));
    } catch (_) {}
  }

  Future<List<dynamic>> history(String me, String other) async {
    final res = await http.get(Uri.parse('$base/chat/history/$me/$other'));
    return jsonDecode(res.body) as List<dynamic>;
  }

  Future<List<dynamic>> alerts(String userId) async {
    final res = await http.get(Uri.parse('$base/alerts/$userId'));
    return jsonDecode(res.body) as List<dynamic>;
  }

  WebSocketChannel connect(String userId) =>
      WebSocketChannel.connect(Uri.parse('$wsBase/ws/chat?user_id=$userId'));

  void sendMessage(WebSocketChannel ws, String recipientId, String text) {
    ws.sink.add(jsonEncode({
      'type': 'message',
      'recipient_id': recipientId,
      'text': text,
    }));
  }
}