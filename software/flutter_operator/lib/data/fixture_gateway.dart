import 'dart:async';

import 'package:flutter/services.dart';

import '../domain/models.dart';
import 'operator_gateway.dart';

/// Dependency-injected development data. Normal builds never construct this.
class FixtureOperatorGateway implements OperatorGateway {
  FixtureOperatorGateway({this.scenario = 'ready', this.tick = true});
  final String scenario;
  final bool tick;
  final _updates = StreamController<GatewayUpdate>.broadcast();
  final _results = <String, CommandResult>{};
  final _cancelled = <String>{};
  final _events = <Json>[];
  final _speech = <Json>[];
  Timer? _timer;
  int _sequence = 0, _generation = 0;
  bool _connected = false;
  Json _mission = {'type': 'none', 'phase': 'idle'};
  Uint8List? _bytes;
  @override
  bool get isFixture => true;
  @override
  Stream<GatewayUpdate> get updates => _updates.stream;

  Json snapshotJson() {
    final now = DateTime.now().toUtc();
    final cameraOffline = scenario == 'offline', stale = scenario == 'stale';
    final denied = scenario == 'denied', audioFault = scenario == 'audio_fault';
    final time = now.toIso8601String();
    Json cap(bool ready, [String? reason]) => {
      'supported': true,
      'ready': ready,
      'reason': ready ? null : reason ?? 'Unavailable in this fixture',
    };
    final roster = <Json>[
      {
        'person_id': 'ishaan',
        'display_name': 'Ishaan',
        'tag_id': 7,
        'tag_family': 'tag36h11',
        'detection_state': scenario == 'lost' ? 'lost' : 'visible',
        'available': scenario != 'lost',
        'reason': scenario == 'lost' ? 'Target not visible' : null,
      },
      {
        'person_id': 'devi',
        'display_name': 'Devi',
        'tag_id': 12,
        'tag_family': 'tag36h11',
        'detection_state': 'visible',
        'available': true,
        'reason': null,
      },
      {
        'person_id': 'manthan',
        'display_name': 'Manthan',
        'tag_id': 18,
        'tag_family': 'tag36h11',
        'detection_state': 'lost',
        'available': false,
        'reason': 'Target not visible',
      },
    ];
    final frame = {
      'frame_id': 'fixture-$_sequence',
      'camera_session_id': 'fixture-camera',
      'width': 1280,
      'height': 720,
      'captured_at': (stale ? now.subtract(const Duration(seconds: 20)) : now)
          .toIso8601String(),
      'valid_for_ms': 4000,
      'rotation': 0,
      'mirrored': false,
      'crop': [0.0, 0.0, 1.0, 1.0],
      'image_path': '/fixture.png',
      'tags': [
        {
          'tag_id': 7,
          'tag_family': 'tag36h11',
          'person_id': 'ishaan',
          'bounds': [0.35, 0.30, 0.14, 0.25],
        },
        {
          'tag_id': 12,
          'tag_family': 'tag36h11',
          'person_id': 'devi',
          'bounds': [0.66, 0.40, 0.10, 0.18],
        },
      ],
    };
    return {
      'api_version': 1,
      'sequence': _sequence,
      'observed_at': time,
      'operator_authorized': !denied,
      'source': 'mock',
      'server_name': 'Local UI fixture',
      'capabilities': {
        'follow': cap(true),
        'land_current': cap(true),
        'land_point': cap(
          !stale && !cameraOffline,
          stale ? 'Camera frame is stale' : 'Camera offline',
        ),
        'land_tag': cap(
          !stale && !cameraOffline,
          stale ? 'Camera frame is stale' : 'Camera offline',
        ),
        'audio_receive': cap(!audioFault, 'Audio node disconnected'),
        'audio_transmit': cap(!audioFault, 'Audio node disconnected'),
        'tts': cap(!audioFault, 'Audio node disconnected'),
      },
      'roster': scenario == 'empty' ? <Json>[] : roster,
      'camera': {
        'state': cameraOffline
            ? 'offline'
            : stale
            ? 'stale'
            : 'live',
        'name': 'Main camera',
        'session_id': 'fixture-camera',
        'transport': 'jpeg',
        'frame': cameraOffline ? null : frame,
      },
      'mission': _mission,
      'audio': {
        'state': audioFault ? 'unavailable' : 'ready',
        'reason': audioFault ? 'Audio node disconnected' : null,
        'max_text_length': 500,
        'voices': [
          {'voice_id': 'fixture-voice', 'name': 'Default voice'},
        ],
        'speech': _speech,
      },
      'components': [
        {
          'id': 'backend',
          'name': 'Backend',
          'state': 'mock',
          'observed_at': time,
          'detail': 'Local UI fixture',
        },
        {
          'id': 'camera',
          'name': 'Camera',
          'state': cameraOffline
              ? 'offline'
              : stale
              ? 'degraded'
              : 'mock',
          'observed_at': time,
          'detail': cameraOffline ? 'No frame available' : 'Fixture test card',
        },
        {
          'id': 'tracking',
          'name': 'Tracking',
          'state': 'mock',
          'observed_at': time,
          'detail': 'Prepared fixture roster',
        },
        {
          'id': 'audio',
          'name': 'Audio node',
          'state': audioFault ? 'offline' : 'mock',
          'observed_at': time,
          'detail': audioFault ? 'Disconnected' : 'No audio device attached',
        },
        {
          'id': 'aircraft',
          'name': 'Aircraft link',
          'state': 'unknown',
          'observed_at': time,
          'detail': 'No aircraft attached',
        },
      ],
      'events': _events,
    };
  }

  OperatorSnapshot get current => OperatorSnapshot.fromJson(snapshotJson());
  void _event(String message) {
    _events.insert(0, {
      'event_id': 'event-$_sequence-${_events.length}',
      'observed_at': DateTime.now().toUtc().toIso8601String(),
      'message': message,
      'severity': 'info',
    });
    if (_events.length > 12) _events.removeLast();
  }

  void _emit() {
    if (!_connected) return;
    _sequence++;
    _updates.add(GatewayUpdate.snapshot(current));
  }

  @override
  Future<OperatorSnapshot> connect(Uri endpoint, String token) async {
    await disconnect();
    _connected = true;
    _sequence = 1;
    _event('UI fixture connected');
    if (tick) {
      _timer = Timer.periodic(const Duration(seconds: 1), (_) => _emit());
    }
    return current;
  }

  @override
  Future<CommandResult> execute(
    String requestId,
    OperatorCommand command,
  ) async {
    if (_results.containsKey(requestId)) return _results[requestId]!;
    final generation = _generation;
    if (command.kind == 'stop') {
      final pending = command.payload['pending_request_id'];
      if (pending is String) _cancelled.add(pending);
    }
    await Future<void>.delayed(const Duration(milliseconds: 180));
    if (!_connected || generation != _generation) {
      return CommandResult(
        requestId,
        CommandDisposition.unknown,
        'Fixture connection closed.',
      );
    }
    if (scenario == 'denied' || scenario == 'rejected') {
      return _results[requestId] = CommandResult(
        requestId,
        CommandDisposition.rejected,
        scenario == 'denied'
            ? 'Operator authorization required'
            : 'Mission not ready',
      );
    }
    switch (command.kind) {
      case 'follow':
        if (!_cancelled.contains(requestId)) {
          _mission = {
            'type': 'follow',
            'phase': 'active',
            'mission_id': 'mission-$requestId',
            'person_id': command.payload['person_id'],
            'request_id': requestId,
            'abort_summary':
                'End this follow task and return task control to the pilot.',
          };
          _event('Fixture follow task active');
        }
      case 'stop':
        _mission = {
          ..._mission,
          'type': _mission['type'] == 'none' ? 'follow' : _mission['type'],
          'phase': 'stopped',
          'request_id': requestId,
        };
        _event('Fixture follow task stopped');
      case 'abort':
        _mission = {..._mission, 'phase': 'aborted', 'request_id': requestId};
        _event('Fixture mission aborted');
      case 'land':
        _mission = {
          'type': 'landing',
          'phase': 'landing',
          'mission_id': 'mission-$requestId',
          'request_id': requestId,
          'abort_summary':
              'Cancel the landing task and return task control to the pilot.',
        };
        _event('Fixture landing request accepted');
        unawaited(
          Future<void>.delayed(const Duration(seconds: 3), () {
            if (generation == _generation &&
                _mission['request_id'] == requestId) {
              _mission = {..._mission, 'phase': 'landed'};
              _event('Fixture landing task completed');
              _emit();
            }
          }),
        );
      case 'speak':
        _speech.insert(0, {
          'request_id': requestId,
          'text': command.payload['text'],
          'state': 'queued',
        });
        if (_speech.length > 6) _speech.removeLast();
        for (final entry in [(1, 'playing'), (3, 'completed')]) {
          unawaited(
            Future<void>.delayed(Duration(seconds: entry.$1), () {
              if (generation != _generation) return;
              for (final item in _speech) {
                if (item['request_id'] == requestId) item['state'] = entry.$2;
              }
              _emit();
            }),
          );
        }
      case 'audio_uplink':
        break;
    }
    final result = CommandResult(requestId, CommandDisposition.accepted);
    _results[requestId] = result;
    _emit();
    return result;
  }

  @override
  Future<CommandResult> lookupCommand(String requestId) async =>
      _results[requestId] ??
      CommandResult(
        requestId,
        CommandDisposition.unknown,
        'Request not found.',
      );
  @override
  Future<CapturedFrame> captureStill() async {
    final raw = Wire.object(snapshotJson()['camera']);
    if (raw['frame'] == null) throw const GatewayFault('Camera offline.');
    final frame = CameraFrame.fromJson({
      ...Wire.object(raw['frame']),
      'valid_for_ms': 15000,
    });
    return CapturedFrame(frame, await frameBytes(frame));
  }

  @override
  Future<Uint8List> frameBytes(CameraFrame frame) async {
    _bytes ??= (await rootBundle.load('assets/fixtures/camera_test_card.png'))
        .buffer
        .asUint8List();
    return _bytes!;
  }

  @override
  Future<Json> negotiateMedia(Json offer) async =>
      throw const GatewayFault('Fixture has no media server.');
  @override
  Future<void> refresh() async => _emit();
  @override
  Future<void> disconnect() async {
    _generation++;
    _connected = false;
    _timer?.cancel();
    _timer = null;
  }

  @override
  void dispose() {
    unawaited(disconnect());
    unawaited(_updates.close());
  }
}
