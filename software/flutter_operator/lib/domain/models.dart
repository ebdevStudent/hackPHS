import 'dart:typed_data';

typedef Json = Map<String, dynamic>;

abstract final class Wire {
  static Json object(dynamic value) {
    if (value is! Map<String, dynamic>) {
      throw const FormatException('Expected an object');
    }
    return value;
  }

  static List<dynamic> list(dynamic value, {int max = 100}) {
    if (value is! List || value.length > max) {
      throw const FormatException('Invalid list');
    }
    return value;
  }

  static String text(dynamic value, {int max = 240, bool empty = false}) {
    if (value is! String ||
        value.runes.length > max ||
        (!empty && value.trim().isEmpty)) {
      throw const FormatException('Invalid text');
    }
    return value;
  }

  static String? optionalText(dynamic value, {int max = 240}) =>
      value == null ? null : text(value, max: max);
  static bool boolean(dynamic value) {
    if (value is! bool) throw const FormatException('Expected a boolean');
    return value;
  }

  static int integer(dynamic value, {int min = 0, int max = 2147483647}) {
    if (value is! int || value < min || value > max) {
      throw const FormatException('Invalid integer');
    }
    return value;
  }

  static double number(dynamic value, {double min = 0, double max = 1}) {
    if (value is! num || !value.isFinite || value < min || value > max) {
      throw const FormatException('Invalid number');
    }
    return value.toDouble();
  }

  static DateTime time(dynamic value) {
    final raw = text(value, max: 40);
    final parsed = DateTime.tryParse(raw);
    if (parsed == null ||
        !parsed.isUtc ||
        raw.length < 20 ||
        raw.substring(0, 19) != parsed.toIso8601String().substring(0, 19)) {
      throw const FormatException('Expected a valid UTC timestamp');
    }
    return parsed;
  }

  static String choice(dynamic value, Set<String> choices) {
    final raw = text(value);
    if (!choices.contains(raw)) throw const FormatException('Unknown state');
    return raw;
  }
}

enum LinkPhase {
  disconnected,
  connecting,
  connected,
  reconnecting,
  unauthorized,
  incompatible,
}

enum Capability {
  follow,
  landCurrent,
  landPoint,
  landTag,
  audioReceive,
  audioTransmit,
  tts;

  String get wireName => switch (this) {
    landCurrent => 'land_current',
    landPoint => 'land_point',
    landTag => 'land_tag',
    audioReceive => 'audio_receive',
    audioTransmit => 'audio_transmit',
    _ => name,
  };
}

class Availability {
  const Availability(this.supported, this.ready, this.reason);
  const Availability.unavailable(String reason) : this(false, false, reason);
  final bool supported, ready;
  final String? reason;
  bool get available => supported && ready;
  factory Availability.fromJson(Json json) {
    final supported = Wire.boolean(json['supported']),
        ready = Wire.boolean(json['ready']);
    final reason = Wire.optionalText(json['reason']);
    if ((ready && !supported) || ((!ready || !supported) && reason == null)) {
      throw const FormatException('Invalid capability');
    }
    return Availability(supported, ready, reason);
  }
}

class RosterPerson {
  const RosterPerson({
    required this.id,
    required this.name,
    this.tagId,
    this.tagFamily,
    required this.state,
    required this.available,
    this.reason,
  });
  final String id, name, state;
  final int? tagId;
  final String? tagFamily, reason;
  final bool available;
  factory RosterPerson.fromJson(Json json) => RosterPerson(
    id: Wire.text(json['person_id'], max: 80),
    name: Wire.text(json['display_name'], max: 100),
    tagId: json['tag_id'] == null
        ? null
        : Wire.integer(json['tag_id'], max: 65535),
    tagFamily: Wire.optionalText(json['tag_family'], max: 40),
    state: Wire.choice(json['detection_state'], {
      'visible',
      'lost',
      'unassigned',
      'unavailable',
      'reacquiring',
    }),
    available: Wire.boolean(json['available']),
    reason: Wire.optionalText(json['reason']),
  );
  String get tagLabel => tagId == null ? 'No tag assigned' : 'Tag $tagId';
  String get stateLabel => switch (state) {
    'visible' => 'Visible',
    'lost' => 'Not visible',
    'reacquiring' => 'Reacquiring',
    'unassigned' => 'Unassigned',
    _ => 'Unavailable',
  };
}

class NormalizedPoint {
  const NormalizedPoint(this.x, this.y);
  final double x, y;
  bool get valid =>
      x.isFinite && y.isFinite && x >= 0 && x <= 1 && y >= 0 && y <= 1;
  Json toJson() => {'x': x, 'y': y};
}

class Crop {
  const Crop(this.x, this.y, this.width, this.height);
  const Crop.full() : this(0, 0, 1, 1);
  final double x, y, width, height;
  factory Crop.fromJson(dynamic raw) {
    final a = Wire.list(raw, max: 4);
    if (a.length != 4) throw const FormatException('Crop needs four values');
    final crop = Crop(
      Wire.number(a[0]),
      Wire.number(a[1]),
      Wire.number(a[2], min: 0.00001),
      Wire.number(a[3], min: 0.00001),
    );
    if (crop.x + crop.width > 1 || crop.y + crop.height > 1) {
      throw const FormatException('Crop exceeds the frame');
    }
    return crop;
  }
}

class TagDetection {
  const TagDetection({
    required this.tagId,
    required this.family,
    required this.bounds,
    this.personId,
  });
  final int tagId;
  final String family;
  final Crop bounds;
  final String? personId;
  factory TagDetection.fromJson(Json json) => TagDetection(
    tagId: Wire.integer(json['tag_id'], max: 65535),
    family: Wire.text(json['tag_family'], max: 40),
    bounds: Crop.fromJson(json['bounds']),
    personId: Wire.optionalText(json['person_id'], max: 80),
  );
}

class CameraFrame {
  const CameraFrame({
    required this.id,
    required this.width,
    required this.height,
    required this.capturedAt,
    required this.validForMs,
    this.imagePath,
    this.rotation = 0,
    this.mirrored = false,
    this.crop = const Crop.full(),
    this.tags = const [],
    this.sessionId,
  });
  final String? sessionId;
  final String id;
  final int width, height, validForMs, rotation;
  final DateTime capturedAt;
  final String? imagePath;
  final bool mirrored;
  final Crop crop;
  final List<TagDetection> tags;
  bool isFresh(DateTime now) {
    final age = now.difference(capturedAt).inMilliseconds;
    return age >= -2000 && age <= validForMs;
  }

  double get aspectRatio {
    final value = width * crop.width / (height * crop.height);
    return rotation == 90 || rotation == 270 ? 1 / value : value;
  }

  factory CameraFrame.fromJson(Json json) {
    final rotation = Wire.integer(json['rotation'], max: 270);
    if (rotation % 90 != 0) throw const FormatException('Unsupported rotation');
    final path = Wire.optionalText(json['image_path'], max: 300);
    if (path != null &&
        (!path.startsWith('/') ||
            path.startsWith('//') ||
            path.contains('?') ||
            path.contains('#') ||
            path.contains('..'))) {
      throw const FormatException('Image path must be a safe same-origin path');
    }
    return CameraFrame(
      id: Wire.text(json['frame_id'], max: 100),
      sessionId: Wire.text(json['camera_session_id'], max: 100),
      width: Wire.integer(json['width'], min: 1, max: 8192),
      height: Wire.integer(json['height'], min: 1, max: 8192),
      capturedAt: Wire.time(json['captured_at']),
      validForMs: Wire.integer(json['valid_for_ms'], min: 1, max: 15000),
      imagePath: path,
      rotation: rotation,
      mirrored: Wire.boolean(json['mirrored']),
      crop: Crop.fromJson(json['crop']),
      tags: Wire.list(json['tags'])
          .map((e) => TagDetection.fromJson(Wire.object(e)))
          .toList(growable: false),
    );
  }
}

class CapturedFrame {
  const CapturedFrame(this.metadata, this.bytes);
  final CameraFrame metadata;
  final Uint8List bytes;
}

class CameraState {
  const CameraState({
    required this.state,
    required this.name,
    this.frame,
    required this.transport,
    this.sessionId,
  });
  final String? sessionId;
  final String state, name, transport;
  final CameraFrame? frame;
  factory CameraState.fromJson(Json json) {
    final value = CameraState(
      state: Wire.choice(json['state'], {
        'live',
        'offline',
        'stale',
        'reconnecting',
        'unsupported',
      }),
      name: Wire.text(json['name'], max: 80),
      transport: Wire.choice(json['transport'], {'webrtc', 'jpeg', 'none'}),
      sessionId: Wire.optionalText(json['session_id'], max: 100),
      frame: json['frame'] == null
          ? null
          : CameraFrame.fromJson(Wire.object(json['frame'])),
    );
    if (value.frame != null && value.frame!.sessionId != value.sessionId) {
      throw const FormatException('Camera frame session does not match');
    }
    return value;
  }
}

class MissionState {
  const MissionState({
    required this.type,
    required this.phase,
    this.id,
    this.personId,
    this.requestId,
    this.reason,
    this.abortSummary,
    this.progress,
  });
  const MissionState.idle() : this(type: 'none', phase: 'idle');
  final String type, phase;
  final String? id, personId, requestId, reason, abortSummary;
  final double? progress;
  bool get busy => {
    'accepted',
    'active',
    'landing',
    'stopping',
    'abort_pending',
    'lost',
    'reacquiring',
  }.contains(phase);
  factory MissionState.fromJson(Json json) {
    final state = MissionState(
      type: Wire.choice(json['type'], {'none', 'follow', 'landing'}),
      phase: Wire.choice(json['phase'], {
        'idle',
        'accepted',
        'active',
        'landing',
        'stopping',
        'stopped',
        'abort_pending',
        'aborted',
        'completed',
        'failed',
        'landed',
        'lost',
        'reacquiring',
      }),
      id: Wire.optionalText(json['mission_id'], max: 100),
      personId: Wire.optionalText(json['person_id'], max: 80),
      requestId: Wire.optionalText(json['request_id'], max: 100),
      reason: Wire.optionalText(json['reason']),
      abortSummary: Wire.optionalText(json['abort_summary']),
      progress: json['progress'] == null ? null : Wire.number(json['progress']),
    );
    if (state.busy && state.id == null) {
      throw const FormatException('Active mission has no identity');
    }
    if (state.type == 'follow' && state.busy && state.personId == null) {
      throw const FormatException('Follow mission has no person identity');
    }
    if ((state.type == 'none' && state.phase != 'idle') ||
        (state.type == 'follow' &&
            {'landing', 'landed'}.contains(state.phase))) {
      throw const FormatException('Mission type does not match its phase');
    }
    return state;
  }
}

class VoiceOption {
  const VoiceOption(this.id, this.name);
  final String id, name;
  factory VoiceOption.fromJson(Json json) => VoiceOption(
    Wire.text(json['voice_id'], max: 100),
    Wire.text(json['name'], max: 80),
  );
}

class SpeechItem {
  const SpeechItem({
    required this.id,
    required this.text,
    required this.state,
    this.reason,
  });
  final String id, text, state;
  final String? reason;
  factory SpeechItem.fromJson(Json json) => SpeechItem(
    id: Wire.text(json['request_id'], max: 100),
    text: Wire.text(json['text'], max: 2000),
    state: Wire.choice(json['state'], {
      'queued',
      'playing',
      'completed',
      'rejected',
      'failed',
    }),
    reason: Wire.optionalText(json['reason']),
  );
}

class AudioState {
  const AudioState({
    required this.state,
    required this.voices,
    required this.maxTextLength,
    required this.speech,
    this.reason,
  });
  final String state;
  final String? reason;
  final List<VoiceOption> voices;
  final int maxTextLength;
  final List<SpeechItem> speech;
  factory AudioState.fromJson(Json json) => AudioState(
    state: Wire.choice(json['state'], {
      'ready',
      'unavailable',
      'connecting',
      'degraded',
    }),
    reason: Wire.optionalText(json['reason']),
    maxTextLength: Wire.integer(json['max_text_length'], min: 1, max: 2000),
    voices: Wire.list(
      json['voices'],
      max: 30,
    ).map((e) => VoiceOption.fromJson(Wire.object(e))).toList(growable: false),
    speech: Wire.list(
      json['speech'],
      max: 30,
    ).map((e) => SpeechItem.fromJson(Wire.object(e))).toList(growable: false),
  );
}

class ComponentState {
  const ComponentState({
    required this.id,
    required this.name,
    required this.state,
    required this.observedAt,
    this.detail,
  });
  final String id, name, state;
  final String? detail;
  final DateTime observedAt;
  factory ComponentState.fromJson(Json json) => ComponentState(
    id: Wire.text(json['id'], max: 80),
    name: Wire.text(json['name'], max: 100),
    state: Wire.choice(json['state'], {
      'ready',
      'degraded',
      'fault',
      'offline',
      'unknown',
      'mock',
    }),
    detail: Wire.optionalText(json['detail']),
    observedAt: Wire.time(json['observed_at']),
  );
}

class BackendEvent {
  const BackendEvent({
    required this.id,
    required this.time,
    required this.message,
    required this.severity,
  });
  final String id, message, severity;
  final DateTime time;
  factory BackendEvent.fromJson(Json json) => BackendEvent(
    id: Wire.text(json['event_id'], max: 100),
    time: Wire.time(json['observed_at']),
    message: Wire.text(json['message']),
    severity: Wire.choice(json['severity'], {'info', 'warning', 'error'}),
  );
}

class OperatorSnapshot {
  const OperatorSnapshot({
    required this.sequence,
    required this.observedAt,
    required this.authorized,
    required this.source,
    required this.serverName,
    required this.capabilities,
    required this.roster,
    required this.camera,
    required this.mission,
    required this.audio,
    required this.components,
    required this.events,
  });
  final int sequence;
  final DateTime observedAt;
  final bool authorized;
  final String source, serverName;
  final Map<Capability, Availability> capabilities;
  final List<RosterPerson> roster;
  final CameraState camera;
  final MissionState mission;
  final AudioState audio;
  final List<ComponentState> components;
  final List<BackendEvent> events;
  factory OperatorSnapshot.fromJson(Json json) {
    if (Wire.integer(json['api_version']) != 1) {
      throw const FormatException('Incompatible API version');
    }
    final caps = Wire.object(json['capabilities']);
    final roster = Wire.list(json['roster'])
        .map((e) => RosterPerson.fromJson(Wire.object(e)))
        .toList(growable: false);
    if (roster.map((e) => e.id).toSet().length != roster.length) {
      throw const FormatException('Duplicate roster identity');
    }
    final events =
        Wire.list(json['events'])
            .map((e) => BackendEvent.fromJson(Wire.object(e)))
            .toList()
          ..sort((a, b) => b.time.compareTo(a.time));
    final observedAt = Wire.time(json['observed_at']);
    final camera = CameraState.fromJson(Wire.object(json['camera']));
    final components = Wire.list(json['components'], max: 30)
        .map((e) => ComponentState.fromJson(Wire.object(e)))
        .toList(growable: false);
    for (final time in [
      if (camera.frame != null) camera.frame!.capturedAt,
      ...components.map((e) => e.observedAt),
      ...events.map((e) => e.time),
    ]) {
      if (time.difference(observedAt).inMilliseconds > 2000) {
        throw const FormatException(
          'Observation timestamp exceeds snapshot time',
        );
      }
    }
    return OperatorSnapshot(
      sequence: Wire.integer(json['sequence']),
      observedAt: observedAt,
      authorized: Wire.boolean(json['operator_authorized']),
      source: Wire.choice(json['source'], {'live', 'mock'}),
      serverName: Wire.text(json['server_name'], max: 100),
      capabilities: Map.unmodifiable({
        for (final c in Capability.values)
          c: caps[c.wireName] == null
              ? const Availability.unavailable('Not supported by this server')
              : Availability.fromJson(Wire.object(caps[c.wireName])),
      }),
      roster: List.unmodifiable(roster),
      camera: camera,
      mission: MissionState.fromJson(Wire.object(json['mission'])),
      audio: AudioState.fromJson(Wire.object(json['audio'])),
      components: List.unmodifiable(components),
      events: List.unmodifiable(events),
    );
  }
}

enum CommandDisposition { accepted, rejected, unknown }

class CommandResult {
  const CommandResult(this.requestId, this.disposition, [this.reason]);
  final String requestId;
  final CommandDisposition disposition;
  final String? reason;
  factory CommandResult.fromJson(Json json) => CommandResult(
    Wire.text(json['request_id'], max: 100),
    CommandDisposition.values.byName(
      Wire.choice(json['state'], {'accepted', 'rejected', 'unknown'}),
    ),
    Wire.optionalText(json['reason']),
  );
}

/// These constructors are the entire mutation surface; there are no axis commands.
class OperatorCommand {
  OperatorCommand._(this.kind, Json payload)
    : payload = Map.unmodifiable(payload);
  final String kind;
  final Json payload;
  factory OperatorCommand.follow(RosterPerson person) =>
      OperatorCommand._('follow', {
        'person_id': person.id,
        'tag_id': person.tagId,
        'tag_family': person.tagFamily,
      });
  factory OperatorCommand.stop(String? missionId, String? pendingRequestId) =>
      OperatorCommand._('stop', {
        'mission_id': missionId,
        'pending_request_id': pendingRequestId,
      });
  factory OperatorCommand.abort(String missionId) =>
      OperatorCommand._('abort', {'mission_id': missionId});
  factory OperatorCommand.landCurrent() =>
      OperatorCommand._('land', {'mode': 'current_position'});
  factory OperatorCommand.landPoint(
    CameraFrame frame,
    NormalizedPoint point,
    TagDetection? tag,
  ) {
    if (!point.valid) throw const FormatException('Landing point is invalid');
    return OperatorCommand._('land', {
      'mode': tag == null ? 'camera_point' : 'apriltag',
      'frame_id': frame.id,
      'point': point.toJson(),
      if (tag != null) 'tag_id': tag.tagId,
      if (tag != null) 'tag_family': tag.family,
    });
  }
  factory OperatorCommand.speak(String text, String? voiceId) =>
      OperatorCommand._('speak', {'text': text, 'voice_id': ?voiceId});
  factory OperatorCommand.uplink(bool enabled, int sequence) =>
      OperatorCommand._('audio_uplink', {
        'enabled': enabled,
        'sequence': sequence,
        'lease_ms': enabled ? 600 : 0,
      });
  Json toJson(String requestId) => {
    'request_id': requestId,
    'kind': kind,
    'payload': payload,
  };
}
