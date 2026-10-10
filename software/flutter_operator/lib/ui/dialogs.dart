import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter/services.dart';

import '../application/operator_controller.dart';
import '../data/operator_gateway.dart';
import '../domain/landing_geometry.dart';
import '../domain/models.dart';
import 'camera_view.dart';
import 'theme.dart';
import 'widgets.dart';

Future<void> _surface(BuildContext context, Widget child) async {
  if (MediaQuery.sizeOf(context).width < 680) {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      sheetAnimationStyle: MediaQuery.disableAnimationsOf(context)
          ? AnimationStyle.noAnimation
          : null,
      useSafeArea: true,
      constraints: BoxConstraints(
        maxHeight: MediaQuery.sizeOf(context).height * .95,
      ),
      builder: (c) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(c).bottom),
        child: SingleChildScrollView(child: child),
      ),
    );
  } else {
    await showDialog<void>(
      context: context,
      animationStyle: MediaQuery.disableAnimationsOf(context)
          ? AnimationStyle.noAnimation
          : null,
      builder: (c) => Dialog(
        child: ConstrainedBox(
          constraints: BoxConstraints(
            maxWidth: 720,
            maxHeight: MediaQuery.sizeOf(c).height * .90,
          ),
          child: SingleChildScrollView(child: child),
        ),
      ),
    );
  }
}

Future<void> showConnection(BuildContext context, OperatorController model) =>
    _surface(context, ConnectionForm(model: model));

class ConnectionForm extends StatefulWidget {
  const ConnectionForm({super.key, required this.model});
  final OperatorController model;
  @override
  State<ConnectionForm> createState() => _ConnectionFormState();
}

class _ConnectionFormState extends State<ConnectionForm> {
  late final TextEditingController endpoint;
  final token = TextEditingController();
  @override
  void initState() {
    super.initState();
    endpoint = TextEditingController(text: widget.model.endpointText);
  }

  @override
  void dispose() {
    endpoint.dispose();
    token.clear();
    token.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: widget.model,
    builder: (context, _) {
      final m = widget.model, connecting = m.phase == LinkPhase.connecting;
      return Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SectionTitle(
              m.connected ? 'Connection' : 'Connect to server',
              trailing: IconButton(
                tooltip: 'Close',
                onPressed: () => Navigator.pop(context),
                icon: const Icon(Icons.close),
              ),
            ),
            const SizedBox(height: 24),
            if (m.connected) ...[
              Text(
                m.snapshot?.serverName ?? 'Server',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              SelectableText(m.endpointText),
              const SizedBox(height: 16),
              Text(
                m.snapshot?.authorized == true
                    ? 'Operator access'
                    : 'Read-only access',
              ),
              const SizedBox(height: 8),
              Text(m.sourceLabel, style: Theme.of(context).textTheme.bodySmall),
              if (m.rosterLocked)
                const Notice('Stop or abort the mission before disconnecting.'),
              const SizedBox(height: 24),
              OutlinedButton(
                onPressed: m.rosterLocked
                    ? null
                    : () async {
                        await m.disconnect();
                        if (context.mounted) Navigator.pop(context);
                      },
                child: const Text('Disconnect'),
              ),
            ] else ...[
              DropdownButtonFormField<String>(
                initialValue: m.networkProfile,
                isExpanded: true,
                decoration: const InputDecoration(labelText: 'Network'),
                items: ['Shared network', 'BallDrone-Demo hotspot']
                    .map(
                      (s) => DropdownMenuItem(
                        value: s,
                        child: Text(
                          s,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    )
                    .toList(),
                onChanged: connecting
                    ? null
                    : (v) => setState(() => m.networkProfile = v!),
              ),
              const SizedBox(height: 20),
              TextField(
                controller: endpoint,
                enabled: !connecting,
                keyboardType: TextInputType.url,
                autocorrect: false,
                decoration: const InputDecoration(
                  labelText: 'Server address',
                  hintText: 'http://<Pi address>:8080',
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Use the Pi’s address on this network.',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 20),
              TextField(
                controller: token,
                enabled: !connecting,
                obscureText: true,
                autocorrect: false,
                enableSuggestions: false,
                decoration: const InputDecoration(labelText: 'Operator token'),
              ),
              const SizedBox(height: 8),
              Text(
                'Leave empty for read-only access.',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              if (m.connectionError != null)
                Notice(m.connectionError!, error: true),
              const SizedBox(height: 24),
              Wrap(
                spacing: 12,
                runSpacing: 8,
                children: [
                  FilledButton(
                    onPressed: connecting
                        ? null
                        : () async {
                            await m.connect(endpoint.text, token.text);
                            if (context.mounted && m.connected) {
                              Navigator.pop(context);
                            }
                          },
                    child: BusyLabel('Connect', busy: connecting),
                  ),
                  TextButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text('Cancel'),
                  ),
                ],
              ),
            ],
          ],
        ),
      );
    },
  );
}

Future<void> showAbort(BuildContext context, OperatorController model) async {
  final mission = model.snapshot?.mission;
  final missionName = model.missionLabel;
  if (mission?.id == null || mission?.abortSummary == null) return;
  await showDialog<void>(
    context: context,
    builder: (context) => AnimatedBuilder(
      animation: model,
      builder: (context, _) => AlertDialog(
        title: const Text('Abort mission'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(missionName, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 12),
            Text(mission!.abortSummary!),
            if (model.snapshot?.mission.id != mission.id)
              const Notice('Mission has changed. Review the current task.'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Palette.danger),
            onPressed:
                model.canAbort && model.snapshot?.mission.id == mission.id
                ? () {
                    Navigator.pop(context);
                    unawaited(model.abort());
                  }
                : null,
            child: const Text('Abort mission'),
          ),
        ],
      ),
    ),
  );
}

Future<void> showLanding(
  BuildContext context,
  OperatorController model, {
  bool pointMode = false,
}) => _surface(context, LandingFlow(model: model, pointMode: pointMode));

class LandingFlow extends StatefulWidget {
  const LandingFlow({super.key, required this.model, required this.pointMode});
  final OperatorController model;
  final bool pointMode;
  @override
  State<LandingFlow> createState() => _LandingFlowState();
}

class _LandingFlowState extends State<LandingFlow> {
  CapturedFrame? frame;
  NormalizedPoint? point;
  TagDetection? tag;
  String mode = 'current', error = '';
  bool loading = false;
  int generation = 0;
  @override
  void initState() {
    super.initState();
    if (widget.pointMode) {
      mode = widget.model.availability(Capability.landPoint).supported
          ? 'point'
          : 'tag';
      unawaited(capture());
    }
  }

  Future<void> capture() async {
    final epoch = ++generation;
    setState(() {
      loading = true;
      error = '';
      frame = null;
      point = null;
      tag = null;
    });
    try {
      final value = await widget.model.gateway.captureStill();
      if (mounted && generation == epoch) setState(() => frame = value);
    } on GatewayFault catch (e) {
      if (mounted && generation == epoch) setState(() => error = e.message);
    } catch (_) {
      if (mounted && generation == epoch) {
        setState(() => error = 'Camera frame unavailable. Try again.');
      }
    } finally {
      if (mounted && generation == epoch) setState(() => loading = false);
    }
  }

  void move(double dx, double dy) {
    setState(
      () => point = NormalizedPoint(
        ((point?.x ?? .5) + dx).clamp(0, 1).toDouble(),
        ((point?.y ?? .5) + dy).clamp(0, 1).toDouble(),
      ),
    );
  }

  @override
  void dispose() {
    generation++;
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: widget.model,
    builder: (context, _) {
      final m = widget.model, compact = MediaQuery.sizeOf(context).width < 680;
      final cap = m.availability(
        mode == 'current'
            ? Capability.landCurrent
            : mode == 'tag'
            ? Capability.landTag
            : Capability.landPoint,
        newMission: true,
      );
      final valid =
          mode == 'current' ||
          (frame != null &&
              frame!.metadata.isFresh(m.now) &&
              frame!.metadata.sessionId == m.snapshot?.camera.sessionId &&
              point != null);
      return Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SectionTitle(
              mode == 'current' ? 'Land here' : 'Choose landing point',
              trailing: IconButton(
                tooltip: 'Close',
                onPressed: () => Navigator.pop(context),
                icon: const Icon(Icons.close),
              ),
            ),
            const SizedBox(height: 20),
            if (mode == 'current')
              const Text('Request landing at the drone’s current location.')
            else ...[
              if (m.availability(Capability.landPoint).supported &&
                  m.availability(Capability.landTag).supported)
                DropdownButtonFormField<String>(
                  initialValue: mode,
                  decoration: const InputDecoration(
                    labelText: 'Landing method',
                  ),
                  items: const [
                    DropdownMenuItem(
                      value: 'point',
                      child: Text('Camera point'),
                    ),
                    DropdownMenuItem(
                      value: 'tag',
                      child: Text('AprilTag aided'),
                    ),
                  ],
                  onChanged: (v) => setState(() {
                    mode = v!;
                    point = null;
                    tag = null;
                  }),
                ),
              const SizedBox(height: 16),
              if (loading)
                const AspectRatio(
                  aspectRatio: 16 / 9,
                  child: Center(child: CircularProgressIndicator()),
                )
              else if (frame != null) ...[
                Focus(
                  onKeyEvent: (_, event) {
                    if (event is! KeyDownEvent || mode != 'point') {
                      return KeyEventResult.ignored;
                    }
                    if (event.logicalKey == LogicalKeyboardKey.arrowLeft) {
                      move(-.02, 0);
                    } else if (event.logicalKey ==
                        LogicalKeyboardKey.arrowRight) {
                      move(.02, 0);
                    } else if (event.logicalKey == LogicalKeyboardKey.arrowUp) {
                      move(0, -.02);
                    } else if (event.logicalKey ==
                        LogicalKeyboardKey.arrowDown) {
                      move(0, .02);
                    } else if (event.logicalKey == LogicalKeyboardKey.enter) {
                      move(0, 0);
                    } else {
                      return KeyEventResult.ignored;
                    }
                    return KeyEventResult.handled;
                  },
                  child: Semantics(
                    label: 'Landing point selection',
                    customSemanticsActions: mode == 'point'
                        ? {
                            const CustomSemanticsAction(
                              label: 'Move marker left',
                            ): () =>
                                move(-.02, 0),
                            const CustomSemanticsAction(
                              label: 'Move marker right',
                            ): () =>
                                move(.02, 0),
                            const CustomSemanticsAction(
                              label: 'Move marker up',
                            ): () =>
                                move(0, -.02),
                            const CustomSemanticsAction(
                              label: 'Move marker down',
                            ): () =>
                                move(0, .02),
                            const CustomSemanticsAction(
                              label: 'Select image center',
                            ): () =>
                                move(0, 0),
                          }
                        : null,
                    child: CameraViewport(
                      model: m,
                      still: frame,
                      point: point,
                      onPoint: frame!.metadata.isFresh(m.now)
                          ? (p) {
                              if (mode == 'tag') {
                                final source = toSourcePoint(
                                  frame!.metadata,
                                  p,
                                );
                                final hits = frame!.metadata.tags.where(
                                  (t) =>
                                      source.x >= t.bounds.x &&
                                      source.x <= t.bounds.x + t.bounds.width &&
                                      source.y >= t.bounds.y &&
                                      source.y <= t.bounds.y + t.bounds.height,
                                );
                                if (hits.isEmpty) return;
                                setState(() {
                                  tag = hits.first;
                                  point = p;
                                });
                              } else {
                                setState(() => point = p);
                              }
                            }
                          : null,
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                if (mode == 'point')
                  Text(
                    point == null
                        ? compact
                              ? 'Tap a point on the image.'
                              : 'Click a point. Arrow keys adjust the selection.'
                        : 'Selected landing point',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                if (mode == 'tag') ...[
                  const SizedBox(height: 8),
                  DropdownButtonFormField<TagDetection>(
                    initialValue: tag,
                    decoration: const InputDecoration(
                      labelText: 'Detected AprilTag',
                    ),
                    items: frame!.metadata.tags
                        .map(
                          (t) => DropdownMenuItem(
                            value: t,
                            child: Text('Tag ${t.tagId} · ${t.family}'),
                          ),
                        )
                        .toList(),
                    onChanged: (t) {
                      if (t == null) return;
                      setState(() {
                        tag = t;
                        point = toDisplayPoint(
                          frame!.metadata,
                          NormalizedPoint(
                            t.bounds.x + t.bounds.width / 2,
                            t.bounds.y + t.bounds.height / 2,
                          ),
                        );
                      });
                    },
                  ),
                ],
                if (frame!.metadata.sessionId != m.snapshot?.camera.sessionId)
                  Notice(
                    'Camera source changed. Capture a new frame.',
                    action: TextButton(
                      onPressed: capture,
                      child: const Text('Capture again'),
                    ),
                  ),
                if (!frame!.metadata.isFresh(m.now))
                  Notice(
                    'Frame expired. Capture a new frame.',
                    action: TextButton(
                      onPressed: capture,
                      child: const Text('Capture again'),
                    ),
                  ),
                const SizedBox(height: 8),
                Text(
                  'Frame captured at ${clockLabel(frame!.metadata.capturedAt)}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
              if (error.isNotEmpty)
                Notice(
                  error,
                  error: true,
                  action: TextButton(
                    onPressed: capture,
                    child: const Text('Try again'),
                  ),
                ),
            ],
            if (!cap.available) Notice(cap.reason ?? 'Landing unavailable'),
            const SizedBox(height: 24),
            Wrap(
              spacing: 12,
              runSpacing: 8,
              children: [
                FilledButton(
                  onPressed: cap.available && valid
                      ? () {
                          if (mode == 'current') {
                            unawaited(m.landCurrent());
                          } else {
                            unawaited(
                              m.landPoint(
                                frame!,
                                toSourcePoint(frame!.metadata, point!),
                                mode == 'tag' ? tag : null,
                              ),
                            );
                          }
                          Navigator.pop(context);
                        }
                      : null,
                  child: const Text('Request landing'),
                ),
                if (mode != 'current' && point != null)
                  OutlinedButton(
                    onPressed: () => setState(() {
                      point = null;
                      tag = null;
                    }),
                    child: const Text('Choose again'),
                  ),
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('Cancel'),
                ),
              ],
            ),
          ],
        ),
      );
    },
  );
}
