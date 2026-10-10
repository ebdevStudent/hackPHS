import 'package:flutter/material.dart';

import '../application/operator_controller.dart';
import '../domain/models.dart';
import 'dialogs.dart';
import 'theme.dart';
import 'widgets.dart';

class SystemView extends StatelessWidget {
  const SystemView({super.key, required this.model, required this.compact});
  final OperatorController model;
  final bool compact;
  @override
  Widget build(BuildContext context) {
    final components = model.snapshot?.components ?? <ComponentState>[];
    return SingleChildScrollView(
      key: const PageStorageKey('system-scroll'),
      padding: EdgeInsets.all(compact ? 16 : 24),
      child: Align(
        alignment: Alignment.topLeft,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1040),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SectionTitle('Subsystems'),
              const SizedBox(height: 12),
              if (components.isEmpty)
                for (final name in [
                  'Backend',
                  'Camera',
                  'Tracking',
                  'Audio node',
                  'Aircraft link',
                ])
                  _SystemRow(
                    name: name,
                    status: 'Unknown',
                    detail: 'No server observation',
                  )
              else
                for (final component in components)
                  Builder(
                    builder: (context) {
                      final stale =
                          !model.fresh ||
                          model.now.difference(component.observedAt).inSeconds >
                              5;
                      final state = stale
                          ? 'Stale'
                          : component.state[0].toUpperCase() +
                                component.state.substring(1);
                      return _SystemRow(
                        name: component.name,
                        status: state,
                        detail: component.detail,
                        age: ageLabel(component.observedAt, model.now),
                        tone: stale
                            ? 'warning'
                            : component.state == 'ready'
                            ? 'ready'
                            : component.state == 'fault'
                            ? 'error'
                            : component.state == 'degraded'
                            ? 'warning'
                            : 'neutral',
                      );
                    },
                  ),
              const SizedBox(height: 28),
              const SectionTitle('Connection'),
              const SizedBox(height: 12),
              _SystemRow(
                name: 'Server',
                status: model.snapshot?.serverName ?? 'Disconnected',
                detail: model.endpointText.isEmpty ? null : model.endpointText,
              ),
              _SystemRow(
                name: 'Access',
                status: model.snapshot == null
                    ? 'Unknown'
                    : model.snapshot!.authorized
                    ? 'Operator'
                    : 'Read only',
              ),
              _SystemRow(
                name: 'Source',
                status: model.snapshot == null
                    ? 'Unknown'
                    : model.snapshot!.source == 'mock'
                    ? 'Mock'
                    : 'Live',
              ),
              _SystemRow(
                name: 'API',
                status: model.snapshot == null ? 'Unknown' : 'Version 1',
              ),
              const SizedBox(height: 16),
              OutlinedButton.icon(
                onPressed: () => showConnection(context, model),
                icon: const Icon(Icons.link, size: 18),
                label: const Text('Connection settings'),
              ),
              if (model.snapshot != null) ...[
                const SizedBox(height: 32),
                const SectionTitle('Capabilities'),
                const SizedBox(height: 12),
                for (final c in Capability.values)
                  Builder(
                    builder: (context) {
                      final a = model.availability(c);
                      final name = switch (c) {
                        Capability.follow => 'Following',
                        Capability.landCurrent => 'Land here',
                        Capability.landPoint => 'Camera-point landing',
                        Capability.landTag => 'AprilTag landing',
                        Capability.audioReceive => 'Incoming audio',
                        Capability.audioTransmit => 'Microphone',
                        Capability.tts => 'Text to speech',
                      };
                      return _SystemRow(
                        name: name,
                        status: a.available
                            ? 'Available'
                            : model.snapshot!.capabilities[c]?.supported == true
                            ? 'Unavailable'
                            : 'Unsupported',
                        detail: a.reason,
                        tone: a.available ? 'ready' : 'neutral',
                      );
                    },
                  ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _SystemRow extends StatelessWidget {
  const _SystemRow({
    required this.name,
    required this.status,
    this.detail,
    this.age,
    this.tone = 'neutral',
  });
  final String name, status, tone;
  final String? detail, age;
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(vertical: 16),
    decoration: const BoxDecoration(
      border: Border(bottom: BorderSide(color: Palette.line)),
    ),
    child: LayoutBuilder(
      builder: (context, c) {
        final narrow =
            c.maxWidth < 560 || MediaQuery.textScalerOf(context).scale(1) > 1.4;
        final info = Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              name,
              style: Theme.of(context).textTheme.bodyMedium
                  ?.copyWith(fontWeight: FontWeight.w600),
            ),
            if (detail != null) ...[
              const SizedBox(height: 5),
              Text(detail!, style: Theme.of(context).textTheme.bodySmall),
            ],
          ],
        );
        final value = Column(
          crossAxisAlignment: narrow
              ? CrossAxisAlignment.start
              : CrossAxisAlignment.end,
          children: [
            StatusText(status, tone: tone),
            if (age != null) ...[
              const SizedBox(height: 5),
              Text(age!, style: Theme.of(context).textTheme.bodySmall),
            ],
          ],
        );
        return narrow
            ? Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [info, const SizedBox(height: 8), value],
              )
            : Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(flex: 3, child: info),
                  const SizedBox(width: 24),
                  Flexible(flex: 2, child: value),
                ],
              );
      },
    ),
  );
}
