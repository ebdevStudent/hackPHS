import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ball_drone/application/operator_controller.dart';
import 'package:ball_drone/data/fixture_gateway.dart';
import 'package:ball_drone/media/media_port.dart';
import 'package:ball_drone/ui/app.dart';
import 'package:ball_drone/ui/dialogs.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() async {
    final loader = FontLoader('Inter')
      ..addFont(rootBundle.load('assets/fonts/Inter.ttf'));
    await loader.load();
  });
  for (final width in [
    360.0,
    390.0,
    430.0,
    600.0,
    800.0,
    1024.0,
    1280.0,
    1440.0,
  ]) {
    for (final destination in [0, 1, 2]) {
      testWidgets('destination $destination at width $width has no overflow', (
        tester,
      ) async {
        tester.view.devicePixelRatio = 1;
        tester.view.physicalSize = Size(width, 900);
        addTearDown(tester.view.reset);
        final m = OperatorController(
          gateway: FixtureOperatorGateway(tick: false),
          media: FixtureMediaPort(),
        );
        await m.connect('http://127.0.0.1', 'fixture');
        m.navigate(destination);
        await tester.pumpWidget(OperatorApp(controller: m));
        await tester.pump(const Duration(milliseconds: 150));
        expect(tester.takeException(), isNull);
        if (width < 680) {
          expect(find.byType(NavigationBar), findsOneWidget);
        } else {
          expect(find.byType(NavigationBar), findsNothing);
        }
        await tester.pumpWidget(const SizedBox.shrink());
      });
    }
  }
  testWidgets('large text, landscape and keyboard retain reachable content', (
    tester,
  ) async {
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(390, 600);
    tester.platformDispatcher.textScaleFactorTestValue = 2;
    addTearDown(tester.view.reset);
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
    final m = OperatorController(
      gateway: FixtureOperatorGateway(tick: false),
      media: FixtureMediaPort(),
    );
    await m.connect('http://127.0.0.1', 'fixture');
    await tester.pumpWidget(OperatorApp(controller: m));
    for (final index in [0, 1, 2]) {
      m.navigate(index);
      await tester.pump();
      expect(tester.takeException(), isNull);
    }
    tester.view.physicalSize = const Size(800, 390);
    m.navigate(1);
    await tester.pump();
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox.shrink());
  });
  testWidgets(
    'resize and destination changes preserve target and speech draft',
    (tester) async {
      tester.view.devicePixelRatio = 1;
      tester.view.physicalSize = const Size(390, 850);
      addTearDown(tester.view.reset);
      final m = OperatorController(
        gateway: FixtureOperatorGateway(tick: false),
        media: FixtureMediaPort(),
      );
      await m.connect('http://127.0.0.1', 'fixture');
      m.selectPerson('devi');
      m.draft.text = 'A retained message.';
      m.navigate(1);
      await tester.pumpWidget(OperatorApp(controller: m));
      tester.view.physicalSize = const Size(1440, 900);
      await tester.pump();
      expect(m.selectedPersonId, 'devi');
      expect(m.draft.text, 'A retained message.');
      expect(find.byType(NavigationBar), findsNothing);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox.shrink());
    },
  );
  testWidgets(
    'connection sheet has persistent labels and keyboard-safe scroll',
    (tester) async {
      tester.view.devicePixelRatio = 1;
      tester.view.physicalSize = const Size(390, 850);
      addTearDown(tester.view.reset);
      final m = OperatorController(
        gateway: FixtureOperatorGateway(tick: false),
        media: FixtureMediaPort(),
      );
      await tester.pumpWidget(OperatorApp(controller: m));
      final context = tester.element(find.byType(Scaffold));
      final dialog = showConnection(context, m);
      await tester.pumpAndSettle();
      expect(find.text('Server address'), findsOneWidget);
      expect(find.text('Operator token'), findsOneWidget);
      tester.view.viewInsets = const FakeViewPadding(bottom: 300);
      await tester.pump();
      expect(tester.takeException(), isNull);
      await tester.tap(find.byTooltip('Close'));
      await tester.pumpAndSettle();
      await dialog;
      await tester.pumpWidget(const SizedBox.shrink());
    },
  );
}
