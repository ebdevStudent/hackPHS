import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';

import 'application/operator_controller.dart';
import 'data/fixture_gateway.dart';
import 'data/rest_gateway.dart';
import 'media/media_port.dart';
import 'ui/app.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  if (kIsWeb) SemanticsBinding.instance.ensureSemantics();
  const preview = bool.fromEnvironment('UI_PREVIEW');
  const initialFixture = String.fromEnvironment(
    'UI_FIXTURE',
    defaultValue: 'ready',
  );
  final fixture = preview && kIsWeb
      ? Uri.base.queryParameters['fixture'] ?? initialFixture
      : initialFixture;
  final controller = OperatorController(
    gateway: preview
        ? FixtureOperatorGateway(scenario: fixture)
        : RestOperatorGateway(),
    media: preview ? FixtureMediaPort() : WebRtcMediaPort(),
  );
  if (preview) await controller.connect('http://127.0.0.1:8080', 'fixture');
  runApp(OperatorApp(controller: controller));
}
