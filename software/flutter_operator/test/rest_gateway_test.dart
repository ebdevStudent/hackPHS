import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:ball_drone/data/fixture_gateway.dart';
import 'package:ball_drone/data/operator_gateway.dart';
import 'package:ball_drone/data/rest_gateway.dart';
import 'package:ball_drone/domain/models.dart';

Json sample() => FixtureOperatorGateway(tick: false).snapshotJson();
http.Response response(Json body) => http.Response(
  jsonEncode(body),
  200,
  headers: {'content-type': 'application/json'},
);
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('token stays in Authorization header, never route/body', () async {
    final requests = <http.Request>[];
    final g = RestOperatorGateway(
      clientFactory: () => MockClient((r) async {
        requests.add(r);
        if (r.url.path.endsWith('/snapshot')) return response(sample());
        final raw = jsonDecode(r.body) as Json;
        return response({'request_id': raw['request_id'], 'state': 'accepted'});
      }),
    );
    await g.connect(validateEndpoint('http://127.0.0.1:8080'), 'private-token');
    final result = await g.execute('id', OperatorCommand.landCurrent());
    expect(result.disposition, CommandDisposition.accepted);
    for (final r in requests) {
      expect(r.headers['Authorization'], 'Bearer private-token');
      expect(r.url.toString(), isNot(contains('private-token')));
      expect(r.body, isNot(contains('private-token')));
    }
    g.dispose();
  });
  for (final status in [401, 403, 404]) {
    test(
      'HTTP $status creates an explicit authorization/protocol fault',
      () async {
        final g = RestOperatorGateway(
          clientFactory: () =>
              MockClient((_) async => http.Response('', status)),
        );
        await expectLater(
          g.connect(validateEndpoint('http://localhost'), ''),
          throwsA(
            isA<GatewayFault>().having(
              (e) => e.phase,
              'phase',
              status == 404 ? LinkPhase.incompatible : LinkPhase.unauthorized,
            ),
          ),
        );
        g.dispose();
      },
    );
  }
  test('string authorization is rejected before controller access', () async {
    final g = RestOperatorGateway(
      clientFactory: () => MockClient(
        (_) async => response(sample()..['operator_authorized'] = 'true'),
      ),
    );
    await expectLater(
      g.connect(validateEndpoint('http://localhost'), 'token'),
      throwsA(
        isA<GatewayFault>().having(
          (e) => e.phase,
          'phase',
          LinkPhase.incompatible,
        ),
      ),
    );
    g.dispose();
  });
  test('mismatched command ACK becomes unknown instead of accepted', () async {
    final g = RestOperatorGateway(
      clientFactory: () => MockClient(
        (r) async => r.url.path.endsWith('/snapshot')
            ? response(sample())
            : response({'request_id': 'different', 'state': 'accepted'}),
      ),
    );
    await g.connect(validateEndpoint('http://localhost'), 'token');
    expect(
      (await g.execute('id', OperatorCommand.landCurrent())).disposition,
      CommandDisposition.unknown,
    );
    g.dispose();
  });
  test('snapshot reordering cannot overwrite newer state', () async {
    var count = 0;
    final sequences = [3, 2, 4];
    final g = RestOperatorGateway(
      clientFactory: () => MockClient(
        (_) async =>
            response(sample()..['sequence'] = sequences[(count++).clamp(0, 2)]),
      ),
    );
    final updates = <GatewayUpdate>[], sub = g.updates.listen(updates.add);
    await g.connect(validateEndpoint('http://localhost'), 'token');
    await g.refresh();
    await Future<void>.delayed(Duration.zero);
    expect(updates, isEmpty);
    await g.refresh();
    await Future<void>.delayed(Duration.zero);
    expect(updates.single.snapshot!.sequence, 4);
    await sub.cancel();
    g.dispose();
  });
  test(
    'late failure from a closed connection cannot fault a new session',
    () async {
      final blocked = Completer<http.Response>();
      var factory = 0;
      final g = RestOperatorGateway(
        clientFactory: () {
          final first = factory++ == 0;
          return MockClient(
            (r) async => first && r.url.path.endsWith('/commands')
                ? blocked.future
                : response(sample()),
          );
        },
      );
      final updates = <GatewayUpdate>[], sub = g.updates.listen(updates.add);
      await g.connect(validateEndpoint('http://localhost'), 'old-token');
      final request = g.execute('old', OperatorCommand.landCurrent());
      await g.connect(validateEndpoint('http://127.0.0.1'), 'new-token');
      blocked.complete(http.Response('', 503));
      expect((await request).disposition, CommandDisposition.unknown);
      await Future<void>.delayed(Duration.zero);
      expect(updates.where((e) => e.fault != null), isEmpty);
      await sub.cancel();
      g.dispose();
    },
  );
  test(
    'lookup reconciles the same identity without another mutation',
    () async {
      var posts = 0;
      final g = RestOperatorGateway(
        clientFactory: () => MockClient((r) async {
          if (r.method == 'POST') posts++;
          return r.url.path.endsWith('/snapshot')
              ? response(sample())
              : response({'request_id': 'uncertain', 'state': 'accepted'});
        }),
      );
      await g.connect(validateEndpoint('http://localhost'), 'token');
      expect((await g.lookupCommand('uncertain')).requestId, 'uncertain');
      expect(posts, 0);
      g.dispose();
    },
  );
  test(
    'concurrent clients sharing a token have distinct media/lease scopes',
    () async {
      final scopes = <String>[];
      RestOperatorGateway makeGateway() => RestOperatorGateway(
        clientFactory: () => MockClient((r) async {
          scopes.add(r.headers['X-Operator-Client']!);
          return response(sample());
        }),
      );
      final first = makeGateway(), second = makeGateway();
      await first.connect(
        validateEndpoint('http://localhost'),
        'shared-operator-token',
      );
      await second.connect(
        validateEndpoint('http://localhost'),
        'shared-operator-token',
      );
      expect(scopes[0], isNot(scopes[1]));
      expect(scopes.every((s) => s.length == 32), isTrue);
      first.dispose();
      second.dispose();
    },
  );
  test('undecodable camera images never become selectable frames', () async {
    final g = RestOperatorGateway(
      clientFactory: () => MockClient(
        (r) async => r.url.path.endsWith('/snapshot')
            ? response(sample())
            : http.Response(
                'not an image',
                200,
                headers: {'content-type': 'image/png'},
              ),
      ),
    );
    final value = await g.connect(
      validateEndpoint('http://localhost'),
      'token',
    );
    await expectLater(
      g.frameBytes(value.camera.frame!),
      throwsA(isA<GatewayFault>()),
    );
    g.dispose();
  });
}
