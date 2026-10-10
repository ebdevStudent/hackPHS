// Run by tools/portable_checks.py against a real, isolated Python process.
// These tests are registered only when an explicit test endpoint is supplied.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ball_drone/application/operator_controller.dart';
import 'package:ball_drone/data/operator_gateway.dart';
import 'package:ball_drone/data/rest_gateway.dart';
import 'package:ball_drone/domain/models.dart';
import 'package:ball_drone/media/media_port.dart';
import 'package:ball_drone/ui/app.dart';

class _RealHttpBinding extends AutomatedTestWidgetsFlutterBinding {
  @override
  bool get overrideHttpClient => false;
}

void main() {
  const endpoint = String.fromEnvironment('BACKEND_URL');
  const token = String.fromEnvironment('BACKEND_TOKEN');
  if (endpoint.isEmpty) return;
  _RealHttpBinding();

  test(
    'real Python auth, frames, follow, loss, stop and request reconciliation',
    () async {
      final gateway = RestOperatorGateway();
      final updates = <OperatorSnapshot>[];
      final listener = gateway.updates.listen((value) {
        if (value.snapshot != null) updates.add(value.snapshot!);
      });
      try {
        final snapshot = await gateway.connect(
          validateEndpoint(endpoint),
          token,
        );
        expect(snapshot.authorized, isTrue);
        expect(snapshot.source, 'mock');
        expect(snapshot.capabilities[Capability.follow]!.available, isTrue);
        expect(
          snapshot.capabilities[Capability.audioTransmit]!.available,
          isFalse,
        );
        final still = await gateway.captureStill();
        expect(still.bytes.length, greaterThan(100));
        expect(still.metadata.tags.map((tag) => tag.tagId), contains(8));
        final id = 'dart-${DateTime.now().microsecondsSinceEpoch}';
        final command = OperatorCommand.follow(snapshot.roster.first);
        expect(
          (await gateway.execute(id, command)).disposition,
          CommandDisposition.accepted,
        );
        expect(
          (await gateway.execute(id, command)).disposition,
          CommandDisposition.accepted,
        );
        expect(
          (await gateway.lookupCommand(id)).disposition,
          CommandDisposition.accepted,
        );
        final deadline = DateTime.now().add(const Duration(seconds: 5));
        while (!updates.any((s) => s.mission.phase == 'active') &&
            DateTime.now().isBefore(deadline)) {
          await gateway.refresh();
          await Future<void>.delayed(const Duration(milliseconds: 100));
        }
        final active = updates.lastWhere((s) => s.mission.phase == 'active');
        expect(active.mission.personId, snapshot.roster.first.id);
        final lossDeadline = DateTime.now().add(const Duration(seconds: 13));
        while (updates.last.mission.phase != 'lost' &&
            DateTime.now().isBefore(lossDeadline)) {
          await gateway.refresh();
          await Future<void>.delayed(const Duration(milliseconds: 100));
        }
        expect(
          updates.last.mission.phase,
          'lost',
          reason: updates.last.mission.reason,
        );
        final reacquireDeadline = DateTime.now().add(
          const Duration(seconds: 4),
        );
        while (updates.last.mission.phase != 'active' &&
            DateTime.now().isBefore(reacquireDeadline)) {
          await gateway.refresh();
          await Future<void>.delayed(const Duration(milliseconds: 100));
        }
        expect(updates.last.mission.phase, 'active');
        expect(
          (await gateway.execute(
            '$id-stop',
            OperatorCommand.stop(active.mission.id, null),
          )).disposition,
          CommandDisposition.accepted,
        );
        await gateway.refresh();
        await Future<void>.delayed(const Duration(milliseconds: 50));
        expect(updates.last.mission.phase, 'stopped');
        expect(
          (await gateway.lookupCommand('not-retained')).disposition,
          CommandDisposition.unknown,
        );
        await gateway.connect(validateEndpoint(endpoint), '');
        final denied = await gateway.execute(
          '$id-denied',
          OperatorCommand.landCurrent(),
        );
        expect(denied.disposition, isNot(CommandDisposition.accepted));
      } finally {
        await listener.cancel();
        await gateway.disconnect();
        gateway.dispose();
      }
    },
  );

  for (final width in [390.0, 1280.0]) {
    testWidgets('real backend snapshot renders at width $width', (
      tester,
    ) async {
      tester.view.devicePixelRatio = 1;
      tester.view.physicalSize = Size(width, 900);
      addTearDown(tester.view.reset);
      final controller = OperatorController(
        gateway: RestOperatorGateway(),
        media: FixtureMediaPort(),
      );
      try {
        await tester.runAsync(() => controller.connect(endpoint, token));
        expect(controller.snapshot!.authorized, isTrue);
        expect(controller.snapshot!.source, 'mock');
        await tester.pumpWidget(
          OperatorApp(controller: controller, disposeController: false),
        );
        await tester.pump(const Duration(milliseconds: 150));
        expect(tester.takeException(), isNull);
        expect(
          find.byType(NavigationBar),
          width < 680 ? findsOneWidget : findsNothing,
        );
        await tester.pumpWidget(const SizedBox.shrink());
        await tester.runAsync(controller.disconnect);
      } finally {
        controller.dispose();
      }
    });
  }
}
