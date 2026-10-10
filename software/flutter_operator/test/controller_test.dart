import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:ball_drone/application/operator_controller.dart';
import 'package:ball_drone/data/fixture_gateway.dart';
import 'package:ball_drone/domain/models.dart';
import 'package:ball_drone/media/media_port.dart';

class ControlledGateway extends FixtureOperatorGateway {
  ControlledGateway({super.scenario}) : super(tick: false);
  final calls = <(String, OperatorCommand, Completer<CommandResult>)>[];
  bool autoComplete = false;
  @override
  Future<CommandResult> execute(String id, OperatorCommand command) {
    final completer = Completer<CommandResult>();
    calls.add((id, command, completer));
    if (autoComplete) {
      completer.complete(CommandResult(id, CommandDisposition.accepted));
    }
    return completer.future;
  }

  void resolve(int index, CommandDisposition state, [String? reason]) {
    final call = calls[index];
    call.$3.complete(CommandResult(call.$1, state, reason));
  }
}

class RecordingMedia extends FixtureMediaPort {
  final enabled = <bool>[];
  @override
  void setMicrophoneEnabled(bool value) => enabled.add(value);
}

Future<OperatorController> make(
  ControlledGateway gateway,
  RecordingMedia media, {
  DateTime Function()? clock,
}) async {
  final m = OperatorController(gateway: gateway, media: media, clock: clock);
  await m.connect('http://127.0.0.1:8080', 'fixture');
  return m;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('no automatic server connection or mission command', () {
    final g = ControlledGateway(), media = RecordingMedia();
    final m = OperatorController(gateway: g, media: media);
    expect(m.phase, LinkPhase.disconnected);
    expect(g.calls, isEmpty);
    expect(m.snapshot, isNull);
    m.dispose();
  });
  test(
    'selection is prepared-roster-only and follows exact identity',
    () async {
      final g = ControlledGateway(), m = await make(g, RecordingMedia());
      m.selectPerson('not-in-roster');
      expect(m.selectedPerson, isNull);
      m.selectPerson('devi');
      final pending = m.follow();
      expect(g.calls.single.$2.payload, {
        'person_id': 'devi',
        'tag_id': 12,
        'tag_family': 'tag36h11',
      });
      g.resolve(0, CommandDisposition.accepted);
      await pending;
      expect(m.snapshot!.mission.phase, 'idle');
      expect(m.missionLabel, contains('Requesting'));
      expect(m.missionLabel, isNot('Following Devi'));
      m.dispose();
    },
  );
  test(
    'a stop supersedes a pending follow and late acceptance cannot erase stop',
    () async {
      final g = ControlledGateway(), m = await make(g, RecordingMedia());
      m.selectPerson('ishaan');
      final start = m.follow();
      expect(m.canStop, isTrue);
      final stop = m.stop();
      expect(g.calls[1].$2.kind, 'stop');
      expect(g.calls[1].$2.payload['pending_request_id'], g.calls[0].$1);
      g.resolve(1, CommandDisposition.accepted);
      await stop;
      final after = m.taskMessage;
      g.resolve(0, CommandDisposition.accepted);
      await start;
      expect(m.taskMessage, after);
      expect(m.missionLabel, contains('stop'));
      m.dispose();
    },
  );
  test(
    'unknown outcome prevents another mission and never becomes success',
    () async {
      final g = ControlledGateway(), m = await make(g, RecordingMedia());
      m.selectPerson('ishaan');
      final start = m.follow();
      g.resolve(0, CommandDisposition.unknown);
      await start;
      expect(m.unknownRequest, isNotNull);
      expect(m.followAvailability.available, isFalse);
      await m.follow();
      expect(g.calls.length, 1);
      expect(m.snapshot!.mission.phase, 'idle');
      m.dispose();
    },
  );
  test('readonly and stale state gate all mutations', () async {
    for (final scenario in ['denied', 'stale']) {
      final g = ControlledGateway(scenario: scenario);
      var clock = DateTime.now().toUtc();
      final m = await make(g, RecordingMedia(), clock: () => clock);
      m.selectPerson('ishaan');
      if (scenario == 'stale') clock = clock.add(const Duration(seconds: 5));
      expect(m.followAvailability.available, isFalse);
      expect(m.availability(Capability.tts).available, isFalse);
      await m.follow();
      await m.landCurrent();
      expect(g.calls, isEmpty);
      m.dispose();
    }
  });
  test('microphone release wins a delayed enable response', () async {
    final g = ControlledGateway(),
        media = RecordingMedia(),
        m = await make(g, media);
    await m.enableMicrophone();
    final press = m.startTalk();
    expect(g.calls.single.$2.payload['enabled'], isTrue);
    m.endTalk();
    expect(media.enabled.last, isFalse);
    final stop = g.calls.last;
    expect(stop.$2.payload['enabled'], isFalse);
    expect(
      stop.$2.payload['sequence'],
      greaterThan(g.calls.first.$2.payload['sequence'] as int),
    );
    g.resolve(0, CommandDisposition.accepted);
    await press;
    expect(m.transmitting, isFalse);
    expect(media.enabled.every((e) => !e), isTrue);
    g.resolve(1, CommandDisposition.accepted);
    m.dispose();
  });
  test('navigation disables locally accepted microphone input', () async {
    final g = ControlledGateway()..autoComplete = true,
        media = RecordingMedia(),
        m = await make(g, media);
    await m.enableMicrophone();
    await m.startTalk();
    expect(m.transmitting, isTrue);
    m.navigate(2);
    expect(m.transmitting, isFalse);
    expect(media.enabled.last, isFalse);
    m.dispose();
  });
  test('TTS unknown blocks repetition and preserves entered text', () async {
    final g = ControlledGateway(), m = await make(g, RecordingMedia());
    m.draft.text = 'Please move to the landing area.';
    final speak = m.speak();
    g.resolve(0, CommandDisposition.unknown);
    await speak;
    expect(m.unknownSpeechRequest, isNotNull);
    await m.speak();
    expect(g.calls.length, 1);
    expect(m.draft.text, 'Please move to the landing area.');
    m.dispose();
  });
  test('rejects an expired or cross-session landing still', () async {
    final g = ControlledGateway(), m = await make(g, RecordingMedia());
    final image = await g.captureStill();
    final expired = CameraFrame(
      id: 'old',
      sessionId: 'fixture-camera',
      width: 1280,
      height: 720,
      capturedAt: DateTime.now().toUtc().subtract(const Duration(seconds: 30)),
      validForMs: 1000,
    );
    await m.landPoint(
      CapturedFrame(expired, image.bytes),
      const NormalizedPoint(.5, .5),
      null,
    );
    expect(g.calls, isEmpty);
    final other = CameraFrame(
      id: 'other',
      sessionId: 'another-session',
      width: 1280,
      height: 720,
      capturedAt: DateTime.now().toUtc(),
      validForMs: 10000,
    );
    await m.landPoint(
      CapturedFrame(other, image.bytes),
      const NormalizedPoint(.5, .5),
      null,
    );
    expect(g.calls, isEmpty);
    m.dispose();
  });
  test('rejection stays visible on an unrelated idle snapshot', () async {
    final g = ControlledGateway(), m = await make(g, RecordingMedia());
    m.selectPerson('ishaan');
    final start = m.follow();
    g.resolve(0, CommandDisposition.rejected, 'Target unavailable');
    await start;
    await g.refresh();
    await Future<void>.delayed(Duration.zero);
    expect(m.taskMessage, 'Target unavailable');
    m.dispose();
  });
  test(
    'reauthorization preserves a pending outcome and still exposes Stop',
    () async {
      final g = ControlledGateway(), m = await make(g, RecordingMedia());
      m.selectPerson('ishaan');
      final start = m.follow();
      final request = g.calls.single.$1;
      await m.connect('http://127.0.0.1:8080', 'new-token');
      expect(m.unknownRequest, request);
      expect(m.canStop, isTrue);
      expect(m.followAvailability.available, isFalse);
      g.resolve(0, CommandDisposition.accepted);
      await start;
      expect(m.unknownRequest, request);
      m.dispose();
    },
  );
  test('switching backend during a pending mission is rejected', () async {
    final g = ControlledGateway(), m = await make(g, RecordingMedia());
    m.selectPerson('devi');
    final start = m.follow();
    await m.connect('http://192.168.4.1:8080', 'token');
    expect(m.connectionError, contains('before switching'));
    expect(m.endpointText, 'http://127.0.0.1:8080');
    g.resolve(0, CommandDisposition.accepted);
    await start;
    m.dispose();
  });
  test('Stop can cancel a follow whose network outcome is unknown', () async {
    final g = ControlledGateway(), m = await make(g, RecordingMedia());
    m.selectPerson('devi');
    final start = m.follow();
    final id = g.calls.first.$1;
    g.resolve(0, CommandDisposition.unknown);
    await start;
    expect(m.canStop, isTrue);
    final stop = m.stop();
    expect(g.calls.last.$2.payload['pending_request_id'], id);
    g.resolve(1, CommandDisposition.accepted);
    await stop;
    m.dispose();
  });
}
