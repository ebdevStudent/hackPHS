import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:ball_drone/data/fixture_gateway.dart';
import 'package:ball_drone/data/operator_gateway.dart';
import 'package:ball_drone/domain/landing_geometry.dart';
import 'package:ball_drone/domain/models.dart';

Json sample() =>
    jsonDecode(jsonEncode(FixtureOperatorGateway(tick: false).snapshotJson()))
        as Json;
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('checked-in backend example is accepted', () {
    final value = OperatorSnapshot.fromJson(
      jsonDecode(File('contract/example-snapshot.json').readAsStringSync()),
    );
    expect(value.source, 'mock');
    expect(value.authorized, isTrue);
    expect(value.roster.single.id, 'ishaan');
  });
  for (final invalid in [
    'true',
    1,
    null,
    {'yes': true},
  ]) {
    test('authorization rejects $invalid', () {
      final raw = sample()..['operator_authorized'] = invalid;
      expect(() => OperatorSnapshot.fromJson(raw), throwsFormatException);
    });
  }
  test('unsupported API version cannot reach widgets', () {
    expect(
      () => OperatorSnapshot.fromJson(sample()..['api_version'] = 2),
      throwsFormatException,
    );
  });
  test('false authorization remains false', () {
    expect(
      OperatorSnapshot.fromJson(sample()..['operator_authorized'] = false)
          .authorized,
      isFalse,
    );
  });
  test('duplicate prepared identities are rejected', () {
    final raw = sample();
    (raw['roster'] as List).add(raw['roster'][0]);
    expect(() => OperatorSnapshot.fromJson(raw), throwsFormatException);
  });
  for (final value in [double.nan, double.infinity, -.1, 1.1, true, '0.5']) {
    test('nonfinite/invalid mission progress $value', () {
      final raw = sample();
      raw['mission'] = {
        'type': 'landing',
        'phase': 'landing',
        'mission_id': 'm',
        'progress': value,
      };
      expect(() => OperatorSnapshot.fromJson(raw), throwsFormatException);
    });
  }
  test('malformed frame provenance and external image paths are rejected', () {
    for (final path in [
      'https://example.com/frame.jpg',
      '//example.com/image',
      '/image?token=secret',
      '/../image',
    ]) {
      final raw = sample();
      raw['camera']['frame']['image_path'] = path;
      expect(() => OperatorSnapshot.fromJson(raw), throwsFormatException);
    }
    final raw = sample();
    raw['camera']['frame']['camera_session_id'] = 'old-session';
    expect(() => OperatorSnapshot.fromJson(raw), throwsFormatException);
  });
  test('overflow/crop/rotation and invalid calendar values are rejected', () {
    for (final entry in [
      ('width', 0),
      ('height', 9000),
      ('valid_for_ms', 0),
      ('rotation', 45),
      ('captured_at', '2026-02-30T12:00:00Z'),
      ('crop', [.9, 0, .5, 1]),
    ]) {
      final raw = sample();
      raw['camera']['frame'][entry.$1] = entry.$2;
      expect(() => OperatorSnapshot.fromJson(raw), throwsFormatException);
    }
  });
  test('event timestamps determine descending order', () {
    final raw = sample()
      ..['events'] = [
        {
          'event_id': 'old',
          'observed_at': '2026-10-09T12:00:00Z',
          'message': 'Old observation',
          'severity': 'info',
        },
        {
          'event_id': 'new',
          'observed_at': '2026-10-09T12:01:00Z',
          'message': 'New observation',
          'severity': 'warning',
        },
      ];
    expect(OperatorSnapshot.fromJson(raw).events.map((e) => e.id), [
      'new',
      'old',
    ]);
  });
  test('mission phase and identity invariants', () {
    for (final m in [
      {'type': 'follow', 'phase': 'active', 'mission_id': 'm'},
      {'type': 'none', 'phase': 'active', 'mission_id': 'm'},
      {'type': 'follow', 'phase': 'landed'},
      {'type': 'landing', 'phase': 'landing'},
    ]) {
      expect(
        () => OperatorSnapshot.fromJson(sample()..['mission'] = m),
        throwsFormatException,
      );
    }
  });
  test('endpoint rejects credentials/query/external plaintext', () {
    for (final address in [
      '',
      'ws://localhost',
      'http://example.com',
      'https://user:password@host',
      'http://localhost/?token=secret',
      'http://localhost/#secret',
    ]) {
      expect(() => validateEndpoint(address), throwsFormatException);
    }
    expect(validateEndpoint('http://192.168.4.1:8080').host, '192.168.4.1');
    expect(validateEndpoint('http://172.31.0.1:8080').host, '172.31.0.1');
    expect(validateEndpoint('https://pi.example.com/bridge').path, '/bridge/');
  });
  test(
    'all mutation payloads are typed, immutable and contain no flight axes',
    () {
      final person = OperatorSnapshot.fromJson(sample()).roster.first;
      final commands = [
        OperatorCommand.follow(person),
        OperatorCommand.stop('m', 'pending'),
        OperatorCommand.abort('m'),
        OperatorCommand.landCurrent(),
        OperatorCommand.speak('A message', 'voice'),
        OperatorCommand.uplink(false, 3),
      ];
      final allowed = {
        'follow': {'person_id', 'tag_id', 'tag_family'},
        'stop': {'mission_id', 'pending_request_id'},
        'abort': {'mission_id'},
        'land': {'mode'},
        'speak': {'text', 'voice_id'},
        'audio_uplink': {'enabled', 'sequence', 'lease_ms'},
      };
      for (final command in commands) {
        expect(command.toJson('request').keys.toSet(), {
          'request_id',
          'kind',
          'payload',
        });
        expect(command.payload.keys.toSet(), allowed[command.kind]);
        expect(() => command.payload['roll'] = 1, throwsUnsupportedError);
      }
    },
  );
  test(
    'independent rotated/cropped reference points map to original frame',
    () {
      final frame = CameraFrame(
        id: 'f',
        sessionId: 's',
        width: 1000,
        height: 500,
        capturedAt: DateTime.utc(2026),
        validForMs: 4000,
        rotation: 90,
        crop: const Crop(.2, .1, .5, .8),
      );
      final source = toSourcePoint(frame, const NormalizedPoint(.25, .75));
      expect(source.x, closeTo(.575, 1e-12));
      expect(source.y, closeTo(.7, 1e-12));
      final mirrored = CameraFrame(
        id: 'f',
        width: 1000,
        height: 500,
        capturedAt: DateTime.utc(2026),
        validForMs: 4000,
        rotation: 90,
        mirrored: true,
        crop: const Crop(.2, .1, .5, .8),
      );
      final mirrorSource = toSourcePoint(
        mirrored,
        const NormalizedPoint(.25, .75),
      );
      expect(mirrorSource.x, closeTo(.325, 1e-12));
      expect(mirrorSource.y, closeTo(.7, 1e-12));
    },
  );
  for (final pair in [
    (0, const NormalizedPoint(0, 0)),
    (90, const NormalizedPoint(0, 1)),
    (180, const NormalizedPoint(1, 1)),
    (270, const NormalizedPoint(1, 0)),
  ]) {
    test('independent upper-left display corner at rotation ${pair.$1}', () {
      final frame = CameraFrame(
        id: 'f',
        width: 640,
        height: 480,
        capturedAt: DateTime.utc(2026),
        validForMs: 1000,
        rotation: pair.$1,
      );
      final actual = toSourcePoint(frame, const NormalizedPoint(0, 0));
      expect(actual.x, pair.$2.x);
      expect(actual.y, pair.$2.y);
    });
  }
  test(
    'all rotation/mirror/crop grid points round-trip without escaping frame',
    () {
      for (final rotation in [0, 90, 180, 270]) {
        for (final mirrored in [false, true]) {
          final frame = CameraFrame(
            id: 'f',
            width: 1280,
            height: 720,
            capturedAt: DateTime.utc(2026),
            validForMs: 1000,
            rotation: rotation,
            mirrored: mirrored,
            crop: const Crop(.1, .2, .7, .6),
          );
          for (var x = 0; x <= 10; x++) {
            for (var y = 0; y <= 10; y++) {
              final p = NormalizedPoint(x / 10, y / 10),
                  source = toSourcePoint(frame, p);
              expect(source.valid, isTrue);
              expect(source.x, inInclusiveRange(.1, .8));
              expect(source.y, inInclusiveRange(.2, .8));
              final back = toDisplayPoint(frame, source);
              expect(back.x, closeTo(p.x, 1e-10));
              expect(back.y, closeTo(p.y, 1e-10));
            }
          }
        }
      }
    },
  );
  test('future nested observations cannot be labelled healthy', () {
    final raw = sample();
    raw['components'][0]['observed_at'] = DateTime.now()
        .toUtc()
        .add(const Duration(minutes: 1))
        .toIso8601String();
    expect(() => OperatorSnapshot.fromJson(raw), throwsFormatException);
  });
  test(
    'hosted HTTPS UI rejects a mixed-content endpoint with useful guidance',
    () {
      expect(
        () => validateEndpoint('http://192.168.4.1:8080', requireHttps: true),
        throwsFormatException,
      );
      expect(
        validateEndpoint('https://pi.example.com', requireHttps: true).scheme,
        'https',
      );
    },
  );
}
