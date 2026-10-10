import 'dart:typed_data';

import '../domain/models.dart';

class GatewayFault implements Exception {
  const GatewayFault(this.message, {this.phase = LinkPhase.reconnecting});
  final String message;
  final LinkPhase phase;
  @override
  String toString() => message;
}

class GatewayUpdate {
  const GatewayUpdate.snapshot(OperatorSnapshot value)
    : snapshot = value,
      fault = null;
  const GatewayUpdate.fault(GatewayFault value)
    : fault = value,
      snapshot = null;
  final OperatorSnapshot? snapshot;
  final GatewayFault? fault;
}

abstract class OperatorGateway {
  Stream<GatewayUpdate> get updates;
  bool get isFixture => false;
  Future<OperatorSnapshot> connect(Uri endpoint, String token);
  Future<void> disconnect();
  Future<CommandResult> execute(String requestId, OperatorCommand command);
  Future<CommandResult> lookupCommand(String requestId);
  Future<CapturedFrame> captureStill();
  Future<Uint8List> frameBytes(CameraFrame frame);
  Future<Json> negotiateMedia(Json offer);
  Future<void> refresh();
  void dispose();
}

Uri validateEndpoint(String input, {bool requireHttps = false}) {
  final uri = Uri.tryParse(input.trim());
  if (uri == null ||
      !{'http', 'https'}.contains(uri.scheme) ||
      uri.host.isEmpty ||
      uri.userInfo.isNotEmpty ||
      uri.hasQuery ||
      uri.hasFragment) {
    throw const FormatException('Enter an HTTP or HTTPS server address.');
  }
  if (requireHttps && uri.scheme != 'https') {
    throw const FormatException('Use an HTTPS server address with this page.');
  }
  if (uri.scheme == 'http') {
    final host = uri.host.toLowerCase();
    final parts = host.split('.').map(int.tryParse).toList();
    final privateV4 =
        parts.length == 4 &&
        parts.every((p) => p != null && p >= 0 && p <= 255) &&
        (parts[0] == 10 ||
            parts[0] == 127 ||
            (parts[0] == 192 && parts[1] == 168) ||
            (parts[0] == 172 && parts[1]! >= 16 && parts[1]! <= 31));
    if (!privateV4 &&
        host != 'localhost' &&
        !host.endsWith('.local') &&
        host != '::1' &&
        !(host.contains(':') &&
            (host.startsWith('fd') || host.startsWith('fc')))) {
      throw const FormatException(
        'Use HTTPS for a server outside the local network.',
      );
    }
  }
  return uri.replace(path: uri.path.endsWith('/') ? uri.path : '${uri.path}/');
}
