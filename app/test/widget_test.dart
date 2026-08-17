import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:aegis_app/api.dart';
import 'package:aegis_app/main.dart';

void main() {
  testWidgets('Aegis app renders the login page', (WidgetTester tester) async {
    final api = AegisApi(
      client: MockClient((request) async => http.Response(
            jsonEncode(<Object>[]),
            200,
            headers: {'content-type': 'application/json'},
          )),
    );

    await tester.pumpWidget(AegisApp(api: api));
    await tester.pump();

    expect(find.text('Aegis'), findsOneWidget);
    expect(find.text('Create & start chatting'), findsOneWidget);
  });
}