import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:http/http.dart' as http;

import '../domain/models.dart';
import 'operator_gateway.dart';

class RestOperatorGateway implements OperatorGateway {
  RestOperatorGateway({http.Client Function()? clientFactory})
    : _clientFactory = clientFactory ?? http.Client.new;
  final http.Client Function() _clientFactory;
  final _updates = StreamController<GatewayUpdate>.broadcast();
  http.Client? _client;
  Uri? _endpoint;
  String _token = '', _clientId = '';
  Timer? _poll;
  int _generation = 0, _lastSequence = -1;
  bool _polling = false;
  @override
  Stream<GatewayUpdate> get updates => _updates.stream;
  @override
  bool get isFixture => false;
  Map<String, String> get _headers => {
    'Accept': 'application/json',
    if (_clientId.isNotEmpty) 'X-Operator-Client': _clientId,
    if (_token.isNotEmpty) 'Authorization': 'Bearer $_token',
  };
  Uri _route(String path) {
    if (_endpoint == null) throw const GatewayFault('Connect a server first.');
    return _endpoint!.resolve('api/ui/v1/$path');
  }

  Future<Json> _json(String path, {Json? body}) async {
    final client = _client;
    if (client == null) throw const GatewayFault('Connection closed.');
    try {
      final uri = _route(path);
      final response =
          await (body == null
                  ? client.get(uri, headers: _headers)
                  : client.post(
                      uri,
                      headers: {
                        ..._headers,
                        'Content-Type': 'application/json',
                      },
                      body: jsonEncode(body),
                    ))
              .timeout(const Duration(seconds: 6));
      if (response.statusCode == 401 || response.statusCode == 403) {
        throw const GatewayFault(
          'Operator token was rejected.',
          phase: LinkPhase.unauthorized,
        );
      }
      if (response.statusCode == 404) {
        throw const GatewayFault(
          'This server does not support the operator API.',
          phase: LinkPhase.incompatible,
        );
      }
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw GatewayFault(
          response.statusCode == 429
              ? 'Server is busy. Try again.'
              : 'Server could not complete the request.',
        );
      }
      if (response.bodyBytes.length > 2 * 1024 * 1024) {
        throw const FormatException('Response too large');
      }
      return Wire.object(jsonDecode(utf8.decode(response.bodyBytes)));
    } on GatewayFault {
      rethrow;
    } on FormatException {
      throw const GatewayFault(
        'Server returned an incompatible response.',
        phase: LinkPhase.incompatible,
      );
    } on TimeoutException {
      throw const GatewayFault('Server did not respond in time.');
    } catch (_) {
      throw const GatewayFault(
        'Server is unreachable. Check the address and network.',
      );
    }
  }

  OperatorSnapshot _parse(Json raw) {
    try {
      return OperatorSnapshot.fromJson(raw);
    } on FormatException {
      throw const GatewayFault(
        'Server returned an incompatible snapshot.',
        phase: LinkPhase.incompatible,
      );
    }
  }

  @override
  Future<OperatorSnapshot> connect(Uri endpoint, String token) async {
    await disconnect();
    if (token.contains('\n') || token.contains('\r') || token.length > 8192) {
      throw const GatewayFault(
        'Operator token is invalid.',
        phase: LinkPhase.unauthorized,
      );
    }
    _endpoint = endpoint;
    _token = token.trim();
    _clientId = List.generate(
      16,
      (_) => Random.secure().nextInt(256),
    ).map((e) => e.toRadixString(16).padLeft(2, '0')).join();
    _client = _clientFactory();
    final generation = _generation;
    final snapshot = _parse(await _json('snapshot'));
    if (generation != _generation) {
      throw const GatewayFault('Connection changed.');
    }
    _lastSequence = snapshot.sequence;
    _poll = Timer.periodic(
      const Duration(seconds: 1),
      (_) => unawaited(refresh()),
    );
    return snapshot;
  }

  @override
  Future<void> refresh() async {
    if (_client == null || _polling) return;
    _polling = true;
    final generation = _generation;
    try {
      final snapshot = _parse(await _json('snapshot'));
      if (generation == _generation && snapshot.sequence > _lastSequence) {
        _lastSequence = snapshot.sequence;
        _updates.add(GatewayUpdate.snapshot(snapshot));
      }
    } on GatewayFault catch (error) {
      if (generation == _generation) _updates.add(GatewayUpdate.fault(error));
    } finally {
      if (generation == _generation) _polling = false;
    }
  }

  @override
  Future<CommandResult> execute(
    String requestId,
    OperatorCommand command,
  ) async {
    final generation = _generation;
    try {
      final result = CommandResult.fromJson(
        await _json('commands', body: command.toJson(requestId)),
      );
      if (generation != _generation) {
        return CommandResult(
          requestId,
          CommandDisposition.unknown,
          'Connection changed.',
        );
      }
      if (result.requestId != requestId) {
        throw const FormatException('Wrong request identity');
      }
      unawaited(refresh());
      return result;
    } on GatewayFault catch (error) {
      if (generation == _generation) _updates.add(GatewayUpdate.fault(error));
      return CommandResult(
        requestId,
        CommandDisposition.unknown,
        error.message,
      );
    } on FormatException {
      return CommandResult(
        requestId,
        CommandDisposition.unknown,
        'Command response could not be validated.',
      );
    }
  }

  @override
  Future<CommandResult> lookupCommand(String requestId) async {
    final result = CommandResult.fromJson(
      await _json('commands/${Uri.encodeComponent(requestId)}'),
    );
    if (result.requestId != requestId) {
      throw const GatewayFault('Command identity does not match.');
    }
    return result;
  }

  @override
  Future<CapturedFrame> captureStill() async {
    final raw = await _json('camera/still', body: {});
    final frame = CameraFrame.fromJson(Wire.object(raw['frame']));
    return CapturedFrame(frame, await frameBytes(frame));
  }

  @override
  Future<Uint8List> frameBytes(CameraFrame frame) async {
    if (frame.imagePath == null || _client == null || _endpoint == null) {
      throw const GatewayFault('Camera frame is unavailable.');
    }
    final uri = _endpoint!.resolve(frame.imagePath!);
    if (uri.origin != _endpoint!.origin) {
      throw const GatewayFault('Camera frame source is invalid.');
    }
    try {
      final response = await _client!
          .get(uri, headers: _headers)
          .timeout(const Duration(seconds: 5));
      if (response.statusCode != 200 ||
          response.bodyBytes.length > 8 * 1024 * 1024 ||
          !{
            'image/jpeg',
            'image/png',
          }.contains(response.headers['content-type']?.split(';').first)) {
        throw const GatewayFault('Camera frame could not be loaded.');
      }
      final buffer = await ui.ImmutableBuffer.fromUint8List(response.bodyBytes);
      try {
        final descriptor = await ui.ImageDescriptor.encoded(buffer);
        try {
          if ((descriptor.width - frame.width * frame.crop.width).abs() > 1 ||
              (descriptor.height - frame.height * frame.crop.height).abs() >
                  1) {
            throw const GatewayFault(
              'Camera frame dimensions do not match its metadata.',
            );
          }
        } finally {
          descriptor.dispose();
        }
      } finally {
        buffer.dispose();
      }
      return response.bodyBytes;
    } on GatewayFault {
      rethrow;
    } catch (_) {
      throw const GatewayFault('Camera frame could not be loaded.');
    }
  }

  @override
  Future<Json> negotiateMedia(Json offer) => _json('media/offer', body: offer);
  @override
  Future<void> disconnect() async {
    _generation++;
    _poll?.cancel();
    _poll = null;
    _client?.close();
    _client = null;
    _endpoint = null;
    _token = '';
    _clientId = '';
    _lastSequence = -1;
    _polling = false;
  }

  @override
  void dispose() {
    unawaited(disconnect());
    unawaited(_updates.close());
  }
}
