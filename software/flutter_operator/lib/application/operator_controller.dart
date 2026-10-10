import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';

import '../data/operator_gateway.dart';
import '../domain/models.dart';
import '../media/media_port.dart';

class OperatorController extends ChangeNotifier {
  OperatorController({
    required this.gateway,
    required this.media,
    DateTime Function()? clock,
  }) : _clock = clock ?? DateTime.now {
    _subscription = gateway.updates.listen(_update);
    media.addListener(_mediaChanged);
    draft.addListener(_draftChanged);
    _tick = Timer.periodic(const Duration(milliseconds: 500), (_) {
      if (_closed) return;
      if (!fresh || !media.ready) endTalk();
      if (_pendingAt != null && now.difference(_pendingAt!).inSeconds >= 9) {
        unknownRequest = _pendingMission;
        _unknownKind = _pendingKind;
        _pendingMission = null;
        _pendingAt = null;
        taskMessage = 'Outcome unknown. Refresh mission status.';
      }
      notifyListeners();
    });
  }
  final OperatorGateway gateway;
  final MediaPort media;
  final DateTime Function() _clock;
  late final StreamSubscription<GatewayUpdate> _subscription;
  late final Timer _tick;
  final TextEditingController draft = TextEditingController();
  OperatorSnapshot? snapshot;
  LinkPhase phase = LinkPhase.disconnected;
  String? connectionError,
      taskMessage,
      audioMessage,
      unknownRequest,
      selectedPersonId,
      voiceId;
  String? unknownSpeechRequest, _speechRequest;
  String endpointText = '', networkProfile = 'Shared network';
  int destination = 0;
  int _generation = 0, _talkEpoch = 0, _uplinkSequence = 0;
  bool _closed = false,
      _loadingFrame = false,
      _talkHeld = false,
      transmitting = false;
  bool microphonePending = false, speechPending = false, _leasePending = false;
  String? _pendingMission, _pendingKind, _unknownKind;
  DateTime? _pendingAt;
  Timer? _lease;
  CameraFrame? displayedFrame;
  Uint8List? frameBytes;
  String? cameraError;
  DateTime get now => _clock().toUtc();
  bool get isFixture => gateway.isFixture;
  bool get connected => phase == LinkPhase.connected;
  bool get fresh {
    final age = snapshot == null
        ? 999999
        : now.difference(snapshot!.observedAt).inMilliseconds;
    return connected && age >= -2000 && age <= 4000;
  }

  bool get missionPending => _pendingMission != null;
  bool get rosterLocked => (snapshot?.mission.busy ?? false) || missionPending;
  bool get talkHeld => _talkHeld;
  bool get cameraFresh =>
      fresh &&
      snapshot?.camera.state == 'live' &&
      (displayedFrame ?? snapshot?.camera.frame)?.isFresh(now) == true;
  RosterPerson? get selectedPerson {
    for (final person in snapshot?.roster ?? <RosterPerson>[]) {
      if (person.id == selectedPersonId) return person;
    }
    return null;
  }

  String requestId() => List.generate(
    16,
    (_) => Random.secure().nextInt(256),
  ).map((e) => e.toRadixString(16).padLeft(2, '0')).join();

  Availability availability(Capability capability, {bool newMission = false}) {
    if (!connected) {
      return const Availability.unavailable('Connect a server first');
    }
    if (!fresh) return const Availability.unavailable('Server status is stale');
    if (snapshot?.authorized != true) {
      return const Availability.unavailable('Operator authorization required');
    }
    if (newMission && (rosterLocked || unknownRequest != null)) {
      return Availability.unavailable(
        unknownRequest != null
            ? 'Refresh the unknown mission outcome'
            : 'Stop the current task before starting another',
      );
    }
    return snapshot!.capabilities[capability] ??
        const Availability.unavailable('Not supported by this server');
  }

  Availability get followAvailability {
    final cap = availability(Capability.follow, newMission: true);
    if (!cap.available) return cap;
    final person = selectedPerson;
    if (person == null) {
      return const Availability.unavailable('Select a person first');
    }
    if (!person.available || person.tagId == null || person.tagFamily == null) {
      return Availability.unavailable(person.reason ?? 'Target is unavailable');
    }
    return cap;
  }

  bool get canStop =>
      fresh &&
      snapshot?.authorized == true &&
      ((snapshot?.mission.type == 'follow' && snapshot?.mission.busy == true) ||
          _pendingKind == 'follow' ||
          (unknownRequest != null && _unknownKind == 'follow'));
  bool get canAbort =>
      fresh &&
      snapshot?.authorized == true &&
      snapshot?.mission.busy == true &&
      snapshot?.mission.abortSummary != null;
  String get missionLabel {
    final mission = snapshot?.mission;
    if (_pendingMission != null) {
      return switch (_pendingKind) {
        'follow' => 'Requesting follow…',
        'land' => 'Requesting landing…',
        'stop' => 'Requesting stop…',
        'abort' => 'Requesting abort…',
        _ => 'Request pending…',
      };
    }
    if (mission == null) return 'No mission active';
    String name = 'selected target';
    for (final p in snapshot!.roster) {
      if (p.id == mission.personId) name = p.name;
    }
    return switch (mission.phase) {
      'active' =>
        mission.type == 'follow' ? 'Following $name' : 'Mission active',
      'accepted' => 'Request accepted',
      'landing' => 'Landing',
      'landed' => 'Landed',
      'stopping' => 'Stopping follow',
      'stopped' => 'Follow stopped',
      'abort_pending' => 'Aborting mission',
      'aborted' => 'Mission aborted',
      'completed' => 'Mission completed',
      'failed' => 'Mission failed',
      'lost' => 'Target lost',
      'reacquiring' => 'Reacquiring target',
      _ => 'No mission active',
    };
  }

  String get sourceLabel => isFixture
      ? 'UI preview · fixture data'
      : snapshot?.source == 'mock'
      ? 'Mock source'
      : 'Live source';
  void _draftChanged() {
    if (!_closed) notifyListeners();
  }

  void _mediaChanged() {
    if (_closed) return;
    if (!media.ready) endTalk();
    notifyListeners();
  }

  void _update(GatewayUpdate update) {
    if (_closed) return;
    if (update.snapshot != null) {
      _accept(update.snapshot!);
    } else if (update.fault != null) {
      phase = update.fault!.phase;
      connectionError = update.fault!.message;
      endTalk();
      media.setListening(false);
      notifyListeners();
    }
  }

  void _accept(OperatorSnapshot value) {
    if (snapshot != null && value.sequence <= snapshot!.sequence) return;
    if (value.observedAt.difference(now).inMilliseconds > 2000) {
      phase = LinkPhase.incompatible;
      connectionError = 'Server timestamp could not be validated.';
      endTalk();
      notifyListeners();
      return;
    }
    final sourceChanged = snapshot?.camera.sessionId != value.camera.sessionId;
    final hadSnapshot = snapshot != null;
    snapshot = value;
    phase = LinkPhase.connected;
    connectionError = null;
    if (sourceChanged) {
      displayedFrame = null;
      frameBytes = null;
      cameraError = null;
      _loadingFrame = false;
    }
    if (sourceChanged && hadSnapshot) {
      endTalk();
      unawaited(media.connect(gateway, value));
    }
    if (selectedPersonId != null &&
        !value.roster.any((e) => e.id == selectedPersonId)) {
      selectedPersonId = null;
    }
    if (selectedPersonId == null && value.mission.personId != null) {
      selectedPersonId = value.mission.personId;
    }
    if (voiceId == null || !value.audio.voices.any((e) => e.id == voiceId)) {
      voiceId = value.audio.voices.isEmpty ? null : value.audio.voices.first.id;
    }
    if (_pendingMission != null && value.mission.requestId == _pendingMission) {
      _pendingMission = null;
      _pendingKind = null;
      _pendingAt = null;
      taskMessage = null;
    }
    if (unknownRequest != null &&
        value.mission.requestId == unknownRequest &&
        value.mission.phase != 'idle') {
      unknownRequest = null;
      _unknownKind = null;
      taskMessage = null;
    }
    if (value.audio.speech.any((e) => e.id == _speechRequest)) {
      audioMessage = null;
    }
    if (value.audio.speech.any((e) => e.id == unknownSpeechRequest)) {
      unknownSpeechRequest = null;
      audioMessage = null;
    }
    if (!fresh || !availability(Capability.audioTransmit).available) endTalk();
    unawaited(_loadFrame());
    notifyListeners();
  }

  Future<void> _loadFrame() async {
    final frame = snapshot?.camera.frame, session = snapshot?.camera.sessionId;
    if (_closed ||
        _loadingFrame ||
        frame == null ||
        frame.imagePath == null ||
        displayedFrame?.id == frame.id) {
      return;
    }
    _loadingFrame = true;
    final generation = _generation;
    try {
      final bytes = await gateway.frameBytes(frame);
      if (!_closed &&
          generation == _generation &&
          snapshot?.camera.sessionId == session) {
        displayedFrame = frame;
        frameBytes = bytes;
        cameraError = null;
      }
    } catch (_) {
      if (!_closed &&
          generation == _generation &&
          snapshot?.camera.sessionId == session) {
        cameraError = 'Camera frame could not be loaded.';
      }
    } finally {
      if (!_closed &&
          generation == _generation &&
          snapshot?.camera.sessionId == session) {
        _loadingFrame = false;
        notifyListeners();
      }
    }
  }

  Future<void> connect(String endpoint, String token) async {
    Uri uri;
    try {
      uri = validateEndpoint(
        endpoint,
        requireHttps: !isFixture && kIsWeb && Uri.base.scheme == 'https',
      );
    } on FormatException catch (error) {
      connectionError = error.message;
      notifyListeners();
      return;
    }
    final sameBackend =
        endpointText.isNotEmpty && validateEndpoint(endpointText) == uri;
    if ((snapshot?.mission.busy == true || missionPending) && !sameBackend) {
      connectionError = 'Stop or abort the mission before switching servers.';
      notifyListeners();
      return;
    }
    final unresolved = sameBackend ? _pendingMission ?? unknownRequest : null;
    final unresolvedKind = sameBackend ? _pendingKind ?? _unknownKind : null;
    if (!sameBackend) {
      selectedPersonId = null;
      voiceId = null;
      unknownSpeechRequest = null;
    }
    if (sameBackend && speechPending) unknownSpeechRequest = _speechRequest;
    speechPending = false;
    microphonePending = false;
    _pendingMission = null;
    _pendingKind = null;
    _pendingAt = null;
    final generation = ++_generation;
    endTalk();
    await media.close();
    snapshot = null;
    displayedFrame = null;
    frameBytes = null;
    _loadingFrame = false;
    phase = LinkPhase.connecting;
    connectionError = null;
    endpointText = endpoint;
    unknownRequest = unresolved;
    _unknownKind = unresolvedKind;
    taskMessage = unresolved == null
        ? null
        : 'Outcome unknown. Refresh mission status.';
    notifyListeners();
    try {
      final value = await gateway.connect(uri, token);
      if (_closed || generation != _generation) return;
      _accept(value);
      await media.connect(gateway, value);
    } on GatewayFault catch (error) {
      if (!_closed && generation == _generation) {
        phase = error.phase;
        connectionError = error.message;
        notifyListeners();
      }
    } catch (_) {
      if (!_closed && generation == _generation) {
        phase = LinkPhase.incompatible;
        connectionError = 'Connection could not be validated.';
        notifyListeners();
      }
    }
  }

  Future<void> disconnect() async {
    endTalk();
    _generation++;
    await media.close();
    await gateway.disconnect();
    if (_closed) return;
    phase = LinkPhase.disconnected;
    snapshot = null;
    displayedFrame = null;
    frameBytes = null;
    _pendingMission = null;
    _pendingKind = null;
    _pendingAt = null;
    unknownRequest = null;
    _unknownKind = null;
    unknownSpeechRequest = null;
    _speechRequest = null;
    speechPending = false;
    microphonePending = false;
    audioMessage = null;
    taskMessage = null;
    connectionError = null;
    notifyListeners();
  }

  void navigate(int index) {
    endTalk();
    destination = index;
    notifyListeners();
  }

  void selectPerson(String id) {
    if (rosterLocked || snapshot?.roster.any((p) => p.id == id) != true) return;
    selectedPersonId = id;
    taskMessage = null;
    notifyListeners();
  }

  void setVoice(String? id) {
    voiceId = id;
    notifyListeners();
  }

  Future<void> follow() async {
    if (!followAvailability.available) {
      taskMessage = followAvailability.reason;
      notifyListeners();
      return;
    }
    await _sendMission(OperatorCommand.follow(selectedPerson!));
  }

  Future<void> stop() async {
    if (!canStop) return;
    await _sendMission(
      OperatorCommand.stop(
        snapshot?.mission.id,
        _pendingKind == 'follow'
            ? _pendingMission ?? unknownRequest
            : _unknownKind == 'follow'
            ? unknownRequest
            : null,
      ),
    );
  }

  Future<void> abort() async {
    if (!canAbort) return;
    await _sendMission(OperatorCommand.abort(snapshot!.mission.id!));
  }

  Future<void> landCurrent() async {
    if (!availability(Capability.landCurrent, newMission: true).available) {
      return;
    }
    await _sendMission(OperatorCommand.landCurrent());
  }

  Future<void> landPoint(
    CapturedFrame frame,
    NormalizedPoint point,
    TagDetection? tag,
  ) async {
    final cap = availability(
      tag == null ? Capability.landPoint : Capability.landTag,
      newMission: true,
    );
    if (!cap.available ||
        !frame.metadata.isFresh(now) ||
        frame.metadata.sessionId != snapshot?.camera.sessionId) {
      taskMessage = cap.reason ?? 'Frame expired. Capture a new frame.';
      notifyListeners();
      return;
    }
    await _sendMission(OperatorCommand.landPoint(frame.metadata, point, tag));
  }

  Future<void> _sendMission(OperatorCommand command) async {
    final id = requestId(), generation = _generation;
    _pendingMission = id;
    _pendingKind = command.kind;
    _pendingAt = now;
    taskMessage = null;
    notifyListeners();
    final result = await gateway.execute(id, command);
    if (_closed || generation != _generation || _pendingMission != id) return;
    if (result.disposition == CommandDisposition.accepted) {
      if (snapshot?.mission.requestId == id) {
        _pendingMission = null;
        _pendingKind = null;
        _pendingAt = null;
      } else {
        taskMessage = 'Request accepted. Waiting for mission state.';
      }
    } else {
      _pendingMission = null;
      _pendingKind = null;
      _pendingAt = null;
      if (result.disposition == CommandDisposition.unknown) {
        unknownRequest = id;
        _unknownKind = command.kind;
        taskMessage = 'Outcome unknown. Refresh mission status.';
      } else {
        taskMessage = result.reason ?? 'Request rejected.';
      }
    }
    notifyListeners();
  }

  Future<void> reconcile() async {
    final id = unknownRequest;
    if (id == null) {
      await gateway.refresh();
      return;
    }
    try {
      final result = await gateway.lookupCommand(id);
      if (_closed || unknownRequest != id) return;
      if (result.disposition == CommandDisposition.rejected) {
        unknownRequest = null;
        _unknownKind = null;
        taskMessage = result.reason ?? 'Request rejected.';
      } else if (result.disposition == CommandDisposition.accepted) {
        taskMessage = 'Request accepted. Waiting for mission state.';
      }
      await gateway.refresh();
    } catch (_) {
      if (!_closed) taskMessage = 'Status unavailable. Try refreshing again.';
    }
    if (!_closed) notifyListeners();
  }

  Future<void> enableMicrophone() async {
    if (microphonePending ||
        !availability(Capability.audioTransmit).available) {
      return;
    }
    final generation = _generation;
    microphonePending = true;
    audioMessage = null;
    notifyListeners();
    await media.enableMicrophone();
    if (_closed || generation != _generation) return;
    microphonePending = false;
    audioMessage = media.error;
    notifyListeners();
  }

  Future<void> retryMedia() async {
    if (snapshot == null || !fresh) return;
    endTalk();
    await media.connect(gateway, snapshot!);
    if (!_closed) notifyListeners();
  }

  void toggleListening() {
    if (!availability(Capability.audioReceive).available || !media.ready) {
      return;
    }
    media.setListening(!media.listening);
  }

  Future<void> startTalk() async {
    if (_talkHeld ||
        !availability(Capability.audioTransmit).available ||
        !media.microphoneReady) {
      return;
    }
    _talkHeld = true;
    final epoch = ++_talkEpoch;
    final sequence = ++_uplinkSequence;
    audioMessage = null;
    notifyListeners();
    final result = await gateway.execute(
      requestId(),
      OperatorCommand.uplink(true, sequence),
    );
    if (_closed || epoch != _talkEpoch || !_talkHeld) return;
    if (result.disposition == CommandDisposition.accepted &&
        fresh &&
        media.ready) {
      transmitting = true;
      media.setMicrophoneEnabled(true);
      _lease = Timer.periodic(
        const Duration(milliseconds: 250),
        (_) => unawaited(_renewLease(epoch)),
      );
    } else {
      audioMessage = result.reason ?? 'Microphone request was rejected.';
      endTalk();
    }
    notifyListeners();
  }

  Future<void> _renewLease(int epoch) async {
    if (_leasePending || epoch != _talkEpoch || !transmitting) return;
    _leasePending = true;
    final result = await gateway.execute(
      requestId(),
      OperatorCommand.uplink(true, ++_uplinkSequence),
    );
    if (epoch == _talkEpoch) _leasePending = false;
    if (!_closed &&
        epoch == _talkEpoch &&
        result.disposition != CommandDisposition.accepted) {
      audioMessage = 'Audio link interrupted.';
      endTalk();
    }
  }

  void endTalk() {
    media.setMicrophoneEnabled(false);
    _lease?.cancel();
    _lease = null;
    _leasePending = false;
    final wasHeld = _talkHeld || transmitting;
    _talkHeld = false;
    transmitting = false;
    _talkEpoch++;
    if (wasHeld && !_closed) {
      unawaited(
        gateway.execute(
          requestId(),
          OperatorCommand.uplink(false, ++_uplinkSequence),
        ),
      );
      notifyListeners();
    }
  }

  Future<void> speak() async {
    final text = draft.text.trim(), max = snapshot?.audio.maxTextLength ?? 500;
    if (speechPending ||
        unknownSpeechRequest != null ||
        text.isEmpty ||
        text.runes.length > max ||
        !availability(Capability.tts).available) {
      return;
    }
    speechPending = true;
    audioMessage = null;
    notifyListeners();
    final generation = _generation;
    final id = requestId();
    _speechRequest = id;
    final result = await gateway.execute(
      id,
      OperatorCommand.speak(text, voiceId),
    );
    if (_closed || generation != _generation) return;
    speechPending = false;
    if (result.disposition == CommandDisposition.unknown) {
      unknownSpeechRequest = id;
    }
    audioMessage = switch (result.disposition) {
      CommandDisposition.accepted => 'Speech request accepted.',
      CommandDisposition.rejected =>
        result.reason ?? 'Speech request rejected.',
      CommandDisposition.unknown =>
        'Speech outcome unknown. Check playback status.',
    };
    notifyListeners();
  }

  Future<void> reconcileSpeech() async {
    final id = unknownSpeechRequest;
    if (id == null) return;
    try {
      final result = await gateway.lookupCommand(id);
      if (_closed || unknownSpeechRequest != id) return;
      if (result.disposition == CommandDisposition.rejected) {
        unknownSpeechRequest = null;
        audioMessage = result.reason ?? 'Speech request rejected.';
      }
      await gateway.refresh();
    } catch (_) {
      if (!_closed) audioMessage = 'Playback status unavailable. Try again.';
    }
    if (!_closed) notifyListeners();
  }

  @override
  void dispose() {
    endTalk();
    _closed = true;
    _tick.cancel();
    _lease?.cancel();
    unawaited(_subscription.cancel());
    media.removeListener(_mediaChanged);
    media.dispose();
    gateway.dispose();
    draft.dispose();
    super.dispose();
  }
}
