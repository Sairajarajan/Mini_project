import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import 'api.dart';

class ChatPage extends StatefulWidget {
  final String userId;
  final String name;

  const ChatPage({super.key, required this.userId, required this.name});

  @override
  State<ChatPage> createState() => _ChatPageState();
}

class _Msg {
  final String text;
  final bool incoming;
  final String? action;
  final double? risk;

  _Msg(this.text, this.incoming, this.action, this.risk);
}

class _ChatPageState extends State<ChatPage> {
  final _api = AegisApi();
  final _input = TextEditingController();
  WebSocketChannel? _ws;
  List<dynamic> _contacts = [];
  dynamic _other;
  final List<_Msg> _messages = [];
  final _scroll = ScrollController();
  Timer? _heartbeat;

  @override
  void initState() {
    super.initState();
    _connect();
    _api.listUsers().then((u) {
      if (mounted) setState(() => _contacts = u);
    });
    _heartbeat = Timer.periodic(const Duration(seconds: 60), (_) {
      _api.heartbeat(widget.userId);
    });
  }

  void _connect() {
    _ws = _api.connect(widget.userId);
    _ws!.stream.listen((raw) {
      final data = jsonDecode(raw as String) as Map<String, dynamic>;
      if (data['type'] == 'message') {
        setState(() => _messages.add(_Msg(data['text'] as String, true, null, null)));
        _scrollDown();
      } else if (data['type'] == 'decision') {
        setState(() {
          final last = _messages.last;
          _messages[_messages.length - 1] = _Msg(
            last.text,
            last.incoming,
            data['action'] as String?,
            (data['risk_score'] as num?)?.toDouble(),
          );
        });
        _scrollDown();
      }
    });
  }

  void _send() {
    final text = _input.text.trim();
    if (text.isEmpty || _other == null || _ws == null) return;
    setState(() => _messages.add(_Msg(text, false, null, null)));
    _input.clear();
    _api.sendMessage(_ws!, _other['user_id'] as String, text);
    _scrollDown();
  }

  Future<void> _loadHistory(dynamic other) async {
    _other = other;
    _messages.clear();
    final list = await _api.history(widget.userId, other['user_id'] as String);
    if (!mounted) return;
    setState(() {
      for (final m in list) {
        _messages.add(_Msg(
          m['text'] as String,
          m['sender_id'] != widget.userId,
          null,
          null,
        ));
      }
    });
    _scrollDown();
  }

  void _scrollDown() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(_scroll.position.maxScrollExtent,
            duration: const Duration(milliseconds: 200), curve: Curves.easeOut);
      }
    });
  }

  @override
  void dispose() {
    _heartbeat?.cancel();
    _ws?.sink.close();
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final others = _contacts.where((c) => c['user_id'] != widget.userId).toList();
    return Scaffold(
      appBar: AppBar(
        title: const Text('Aegis'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: Center(child: Text(widget.name, style: const TextStyle(fontWeight: FontWeight.w600))),
          ),
        ],
      ),
      body: Row(
        children: [
          SizedBox(
            width: 200,
            child: ListView(
              padding: const EdgeInsets.all(8),
              children: [
                const Padding(
                  padding: EdgeInsets.all(8),
                  child: Text('Contacts', style: TextStyle(fontWeight: FontWeight.bold)),
                ),
                for (final c in others)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: OutlinedButton(
                      style: _other?['user_id'] == c['user_id']
                          ? OutlinedButton.styleFrom(backgroundColor: Colors.blue.shade100)
                          : null,
                      onPressed: () => _loadHistory(c),
                      child: Text(c['name'] as String),
                    ),
                  ),
              ],
            ),
          ),
          const VerticalDivider(width: 1),
          Expanded(
            child: Column(
              children: [
                Expanded(
                  child: ListView.builder(
                    controller: _scroll,
                    padding: const EdgeInsets.all(12),
                    itemCount: _messages.length,
                    itemBuilder: (_, i) {
                      final m = _messages[i];
                      final align = m.incoming ? CrossAxisAlignment.start : CrossAxisAlignment.end;
                      return Align(
                        alignment: m.incoming ? Alignment.centerLeft : Alignment.centerRight,
                        child: Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          decoration: BoxDecoration(
                            color: m.incoming ? Colors.grey.shade300 : Colors.blue.shade600,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.6),
                          child: Column(
                            crossAxisAlignment: align,
                            children: [
                              Text(m.text,
                                  style: TextStyle(
                                      color: m.incoming ? Colors.black : Colors.white)),
                              if (m.action != null)
                                Padding(
                                  padding: const EdgeInsets.only(top: 4),
                                  child: Text(
                                    '${m.action} · risk ${m.risk}',
                                    style: TextStyle(
                                        fontSize: 11,
                                        color: m.incoming ? Colors.black54 : Colors.white70,
                                        fontWeight: FontWeight.w600),
                                  ),
                                ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.all(12),
                  child: Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _input,
                          decoration: const InputDecoration(
                            hintText: 'Type a message... (Aegis checks it before delivery)',
                            border: OutlineInputBorder(),
                          ),
                          onSubmitted: (_) => _send(),
                        ),
                      ),
                      const SizedBox(width: 8),
                      IconButton.filled(
                        onPressed: _send,
                        icon: const Icon(Icons.send),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}