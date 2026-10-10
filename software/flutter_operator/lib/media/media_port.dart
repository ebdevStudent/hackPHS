import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_webrtc/flutter_webrtc.dart';

import '../data/operator_gateway.dart';
import '../domain/models.dart';

abstract class MediaPort extends ChangeNotifier {
  RTCVideoRenderer? get renderer => null;
  bool get ready;
  bool get microphoneReady;
  bool get listening;
  String? get error;
  Future<void> connect(OperatorGateway gateway, OperatorSnapshot snapshot);
  Future<void> enableMicrophone();
  void setMicrophoneEnabled(bool enabled);
  void setListening(bool enabled);
  Future<void> close();
}

class FixtureMediaPort extends MediaPort {
  bool _ready = false, _microphone = false, _listening = false;
  @override
  bool get ready => _ready;
  @override
  bool get microphoneReady => _microphone;
  @override
  bool get listening => _listening;
  @override
  String? get error => null;
  @override
  Future<void> connect(
    OperatorGateway gateway,
    OperatorSnapshot snapshot,
  ) async {
    _ready = true;
    notifyListeners();
  }

  @override
  Future<void> enableMicrophone() async {
    _microphone = true;
    notifyListeners();
  }

  @override
  void setMicrophoneEnabled(bool enabled) {}
  @override
  void setListening(bool enabled) {
    _listening = enabled;
    notifyListeners();
  }

  @override
  Future<void> close() async {
    _ready = false;
    _microphone = false;
    _listening = false;
  }
}

/// Non-trickle offer/answer. No camera capture or microphone permission on startup.
class WebRtcMediaPort extends MediaPort {
  RTCVideoRenderer? _renderer;
  RTCPeerConnection? _peer;
  RTCRtpTransceiver? _audio;
  MediaStream? _local, _remote;
  OperatorGateway? _gateway;
  bool _ready = false, _microphone = false, _listening = false;
  String? _error, _sessionId;
  int _epoch = 0;
  bool _disposed = false;
  @override
  RTCVideoRenderer? get renderer => _renderer;
  @override
  bool get ready => _ready;
  @override
  bool get microphoneReady => _microphone;
  @override
  bool get listening => _listening;
  @override
  String? get error => _error;
  void _notify() {
    if (!_disposed) notifyListeners();
  }

  @override
  Future<void> connect(
    OperatorGateway gateway,
    OperatorSnapshot snapshot,
  ) async {
    final closing = close();
    final epoch = _epoch;
    await closing;
    if (epoch != _epoch) return;
    _gateway = gateway;
    _error = null;
    if (snapshot.camera.transport != 'webrtc' &&
        !(snapshot.capabilities[Capability.audioReceive]?.supported ?? false)) {
      return;
    }
    try {
      final renderer = RTCVideoRenderer();
      await renderer.initialize();
      if (epoch != _epoch) {
        await renderer.dispose();
        return;
      }
      _renderer = renderer;
      final peer = await createPeerConnection({
        'iceServers': [],
        'sdpSemantics': 'unified-plan',
      });
      if (epoch != _epoch) {
        await peer.close();
        return;
      }
      _peer = peer;
      peer.onTrack = (event) async {
        if (epoch != _epoch) return;
        if (event.track.kind == 'audio') {
          event.track.enabled = _listening && _ready;
        }
        if (event.streams.isNotEmpty) {
          _remote = event.streams.first;
        } else {
          _remote ??= await createLocalMediaStream('remote');
          await _remote!.addTrack(event.track);
        }
        if (epoch != _epoch) return;
        _renderer?.srcObject = _remote;
        setListening(_listening);
        _notify();
      };
      peer.onConnectionState = (state) {
        if (epoch != _epoch) return;
        if (state == RTCPeerConnectionState.RTCPeerConnectionStateFailed ||
            state ==
                RTCPeerConnectionState.RTCPeerConnectionStateDisconnected) {
          setMicrophoneEnabled(false);
          _ready = false;
          _error = 'Media connection interrupted.';
          _notify();
        }
      };
      await peer.addTransceiver(
        kind: RTCRtpMediaType.RTCRtpMediaTypeVideo,
        init: RTCRtpTransceiverInit(direction: TransceiverDirection.RecvOnly),
      );
      _audio = await peer.addTransceiver(
        kind: RTCRtpMediaType.RTCRtpMediaTypeAudio,
        init: RTCRtpTransceiverInit(direction: TransceiverDirection.RecvOnly),
      );
      await _negotiate(epoch);
      if (epoch == _epoch) {
        _ready = true;
        _notify();
      }
    } catch (_) {
      if (epoch == _epoch) {
        _error = 'Media connection unavailable.';
        _ready = false;
        _notify();
      }
    }
  }

  Future<void> _negotiate(int epoch) async {
    final peer = _peer, gateway = _gateway;
    if (peer == null || gateway == null) {
      throw const GatewayFault('Media session closed.');
    }
    final gathered = Completer<void>();
    peer.onIceGatheringState = (state) {
      if (state == RTCIceGatheringState.RTCIceGatheringStateComplete &&
          !gathered.isCompleted) {
        gathered.complete();
      }
    };
    await peer.setLocalDescription(await peer.createOffer());
    if (peer.iceGatheringState !=
        RTCIceGatheringState.RTCIceGatheringStateComplete) {
      await gathered.future.timeout(const Duration(seconds: 8));
    }
    if (epoch != _epoch) return;
    final local = await peer.getLocalDescription();
    final answer = await gateway.negotiateMedia({
      'type': 'offer',
      'sdp': local!.sdp,
      if (_sessionId != null) 'session_id': _sessionId,
    });
    if (epoch != _epoch) return;
    _sessionId = Wire.text(answer['session_id'], max: 100);
    await peer.setRemoteDescription(
      RTCSessionDescription(Wire.text(answer['sdp'], max: 300000), 'answer'),
    );
  }

  @override
  Future<void> enableMicrophone() async {
    final epoch = _epoch;
    if (!_ready || _peer == null) return;
    _error = null;
    MediaStream stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        'audio': {
          'echoCancellation': true,
          'noiseSuppression': true,
          'autoGainControl': true,
        },
        'video': false,
      });
    } catch (_) {
      if (epoch == _epoch) {
        _error = 'Microphone permission was denied. Enable it in settings.';
        _notify();
      }
      return;
    }
    for (final track in stream.getAudioTracks()) {
      track.enabled = false;
    }
    if (epoch != _epoch || _disposed) {
      await stream.dispose();
      return;
    }
    try {
      _local = stream;
      await _audio!.sender.replaceTrack(stream.getAudioTracks().first);
      await _audio!.setDirection(TransceiverDirection.SendRecv);
      await _negotiate(epoch);
      if (epoch == _epoch) {
        _microphone = true;
        _notify();
      }
    } catch (_) {
      for (final track in stream.getAudioTracks()) {
        await track.stop();
      }
      await stream.dispose();
      _local = null;
      if (epoch == _epoch) {
        _microphone = false;
        _error = 'Microphone connection failed. Try again.';
        _notify();
      }
    }
  }

  @override
  void setMicrophoneEnabled(bool enabled) {
    for (final track in _local?.getAudioTracks() ?? <MediaStreamTrack>[]) {
      track.enabled = enabled && _ready && _microphone;
    }
  }

  @override
  void setListening(bool enabled) {
    _listening = enabled && _ready;
    for (final track in _remote?.getAudioTracks() ?? <MediaStreamTrack>[]) {
      track.enabled = _listening;
    }
    // Native renderer.muted only supports local tracks. Web uses its audio element.
    if (kIsWeb && _renderer?.srcObject != null) _renderer!.muted = !_listening;
    _notify();
  }

  @override
  Future<void> close() async {
    _epoch++;
    setMicrophoneEnabled(false);
    _ready = false;
    _microphone = false;
    _listening = false;
    _sessionId = null;
    final local = _local, peer = _peer, renderer = _renderer;
    _local = null;
    _remote = null;
    _peer = null;
    _renderer = null;
    _gateway = null;
    if (local != null) {
      for (final track in local.getAudioTracks()) {
        await track.stop();
      }
      await local.dispose();
    }
    await peer?.close();
    await renderer?.dispose();
  }

  @override
  void dispose() {
    _disposed = true;
    unawaited(close());
    super.dispose();
  }
}
