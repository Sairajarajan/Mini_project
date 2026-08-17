import 'package:flutter/material.dart';

import 'api.dart';
import 'login_page.dart';

void main() {
  runApp(const AegisApp());
}

class AegisApp extends StatelessWidget {
  const AegisApp({super.key, this.api});
  final AegisApi? api;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Aegis',
      theme: ThemeData(colorSchemeSeed: Colors.blue, useMaterial3: true),
      home: LoginPage(api: api),
    );
  }
}