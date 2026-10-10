import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:ball_drone/main.dart' as app;
import 'package:ball_drone/ui/camera_view.dart';
import 'package:ball_drone/ui/audio.dart';

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  testWidgets('Android operator flows and actual rendered screens', (
    tester,
  ) async {
    await app.main();
    await tester.pumpAndSettle();
    await binding.convertFlutterSurfaceToImage();
    await tester.pump();
    await binding.takeScreenshot('android-live');
    expect(find.byType(NavigationBar), findsOneWidget);
    expect(find.text('UI preview · fixture data'), findsOneWidget);
    await tester.tap(find.text('Select person'));
    await tester.pumpAndSettle();
    await binding.takeScreenshot('android-roster');
    await tester.tap(find.text('Ishaan').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Start following'));
    await tester.pump(const Duration(seconds: 1));
    expect(find.text('Following Ishaan'), findsOneWidget);
    await binding.takeScreenshot('android-following');
    await tester.ensureVisible(find.text('Abort mission'));
    await tester.tap(find.text('Abort mission'));
    await tester.pumpAndSettle();
    await binding.takeScreenshot('android-abort-review');
    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Stop following'));
    await tester.tap(find.text('Stop following'));
    await tester.pump(const Duration(seconds: 1));
    expect(find.text('Follow stopped'), findsOneWidget);
    await tester.ensureVisible(find.text('Land here'));
    await tester.tap(find.text('Land here'));
    await tester.pumpAndSettle();
    await binding.takeScreenshot('android-landing-review');
    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Choose landing point'));
    await tester.tap(find.text('Choose landing point'));
    await tester.pumpAndSettle();
    final camera = find.byType(CameraViewport).last;
    await tester.tap(camera);
    await tester.pump();
    await binding.takeScreenshot('android-landing-point');
    await tester.tap(find.text('Request landing'));
    await tester.pump(const Duration(seconds: 4));
    expect(find.text('Landed'), findsOneWidget);
    await tester.tap(
      find.widgetWithIcon(NavigationDestination, Icons.volume_up_outlined),
    );
    await tester.pumpAndSettle();
    await binding.takeScreenshot('android-audio');
    await tester.tap(find.text('Listen'));
    await tester.pump();
    expect(find.text('Listening · fixture'), findsOneWidget);
    await tester.tap(find.text('Enable microphone'));
    await tester.pump();
    final talk = find.byType(TalkButton).last;
    final gesture = await tester.startGesture(tester.getCenter(talk));
    await tester.pump(const Duration(milliseconds: 600));
    expect(find.text('Talking…'), findsOneWidget);
    await binding.takeScreenshot('android-talking');
    await gesture.up();
    await tester.pump();
    expect(find.text('Talking…'), findsNothing);
    await tester.enterText(
      find.byKey(const ValueKey('tts-draft')),
      'Please prepare the landing area.',
    );
    await tester.pump();
    await tester.ensureVisible(find.text('Speak'));
    expect(
      tester
          .widget<FilledButton>(find.widgetWithText(FilledButton, 'Speak'))
          .onPressed,
      isNotNull,
    );
    await tester.tap(find.text('Speak'));
    await tester.pump(const Duration(milliseconds: 350));
    for (var i = 0; i < 24 && find.text('Completed').evaluate().isEmpty; i++) {
      await tester.pump(const Duration(milliseconds: 250));
    }
    await binding.takeScreenshot('android-speech');
    expect(find.text('Completed'), findsWidgets);
    await tester.tap(
      find.widgetWithIcon(NavigationDestination, Icons.tune_outlined),
    );
    await tester.pumpAndSettle();
    await binding.takeScreenshot('android-system');
    expect(find.text('Subsystems'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
