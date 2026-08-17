import 'package:flutter/material.dart';

import 'api.dart';
import 'chat_page.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key, this.api});
  final AegisApi? api;

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  late final AegisApi _api = widget.api ?? AegisApi();
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _parent = TextEditingController();
  List<dynamic> _users = [];
  bool _creating = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final users = await _api.listUsers();
    if (mounted) setState(() => _users = users);
  }

  Future<void> _create() async {
    if (_name.text.trim().isEmpty) return;
    setState(() => _creating = true);
    final id = 'u${DateTime.now().millisecondsSinceEpoch.toRadixString(36)}';
    await _api.upsertUser(id, _name.text, _email.text, _parent.text);
    if (!mounted) return;
    setState(() => _creating = false);
    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => ChatPage(userId: id, name: _name.text),
    ));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Icon(Icons.shield, size: 56, color: Colors.blue),
                const SizedBox(height: 8),
                const Text('Aegis',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold)),
                const Text('Child Chat Guardian',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.grey)),
                const SizedBox(height: 24),
                if (_users.isNotEmpty) ...[
                  const Text('Existing profiles', style: TextStyle(fontWeight: FontWeight.w600)),
                  const SizedBox(height: 8),
                  for (final u in _users)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: OutlinedButton(
                        onPressed: () => Navigator.of(context).push(MaterialPageRoute(
                          builder: (_) => ChatPage(
                            userId: u['user_id'] as String,
                            name: u['name'] as String,
                          ),
                        )),
                        child: Text(u['name'] as String),
                      ),
                    ),
                  const Divider(height: 24),
                ],
                const Text('New profile', style: TextStyle(fontWeight: FontWeight.w600)),
                const SizedBox(height: 8),
                TextField(controller: _name, decoration: const InputDecoration(labelText: 'Child name')),
                TextField(controller: _email, decoration: const InputDecoration(labelText: 'Child email')),
                TextField(controller: _parent, decoration: const InputDecoration(labelText: 'Parent email')),
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: _creating ? null : _create,
                  child: const Text('Create & start chatting'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}