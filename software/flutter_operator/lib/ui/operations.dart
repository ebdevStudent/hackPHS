import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter/services.dart';

import '../application/operator_controller.dart';
import '../domain/models.dart';
import 'audio.dart';
import 'camera_view.dart';
import 'dialogs.dart';
import 'theme.dart';
import 'widgets.dart';

class OperationsView extends StatefulWidget {
  const OperationsView({
    super.key,
    required this.model,
    required this.wide,
    required this.compact,
  });
  final OperatorController model;
  final bool wide, compact;
  @override
  State<OperationsView> createState() => _OperationsViewState();
}

class _OperationsViewState extends State<OperationsView> {
  double rosterWidth = 200, inspectorWidth = 248;
  @override
  Widget build(BuildContext context) {
    final m = widget.model;
    if (!widget.wide) {
      return SingleChildScrollView(
        key: const PageStorageKey('compact-live'),
        padding: EdgeInsets.all(widget.compact ? 16 : 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _CameraHeader(model: m),
            const SizedBox(height: 12),
            CameraViewport(model: m),
            if (m.cameraError != null) Notice(m.cameraError!, error: true),
            const SizedBox(height: 20),
            FollowControls(
              model: m,
              choosePerson: true,
              desktop: !widget.compact,
            ),
            const SizedBox(height: 24),
            const Divider(height: 1),
            const SizedBox(height: 24),
            MissionPanel(model: m),
            const SizedBox(height: 24),
            const Divider(height: 1),
            const SizedBox(height: 20),
            const SectionTitle('Recent events'),
            EventList(model: m, limit: 4),
          ],
        ),
      );
    }
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 12, 24, 24),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            width: rosterWidth,
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Padding(
                    padding: EdgeInsets.fromLTRB(12, 8, 12, 16),
                    child: SectionTitle('People'),
                  ),
                  RosterList(model: m),
                ],
              ),
            ),
          ),
          _PaneDivider(
            onDrag: (delta) => setState(
              () => rosterWidth = (rosterWidth + delta)
                  .clamp(176, 248)
                  .toDouble(),
            ),
          ),
          Expanded(
            child: Column(
              children: [
                Expanded(
                  child: SingleChildScrollView(
                    key: const PageStorageKey('desktop-camera'),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _CameraHeader(model: m),
                        const SizedBox(height: 12),
                        CameraViewport(model: m),
                        if (m.cameraError != null)
                          Notice(m.cameraError!, error: true),
                        const SizedBox(height: 24),
                        FollowControls(model: m, desktop: true),
                        const SizedBox(height: 20),
                      ],
                    ),
                  ),
                ),
                const Divider(height: 1),
                const SizedBox(height: 12),
                AudioDock(model: m),
              ],
            ),
          ),
          _PaneDivider(
            onDrag: (delta) => setState(
              () => inspectorWidth = (inspectorWidth - delta)
                  .clamp(224, 280)
                  .toDouble(),
            ),
          ),
          SizedBox(
            width: inspectorWidth,
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 8),
                  MissionPanel(model: m),
                  const SizedBox(height: 28),
                  const Divider(height: 1),
                  const SizedBox(height: 24),
                  const SectionTitle('Recent events'),
                  const SizedBox(height: 4),
                  EventList(model: m),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _PaneDivider extends StatefulWidget {
  const _PaneDivider({required this.onDrag});
  final ValueChanged<double> onDrag;
  @override
  State<_PaneDivider> createState() => _PaneDividerState();
}

class _PaneDividerState extends State<_PaneDivider> {
  bool focused = false, hovered = false;
  @override
  Widget build(BuildContext context) => Semantics(
    label: 'Resize inspector',
    customSemanticsActions: {
      const CustomSemanticsAction(label: 'Move divider left'): () =>
          widget.onDrag(-16),
      const CustomSemanticsAction(label: 'Move divider right'): () =>
          widget.onDrag(16),
    },
    child: Focus(
      onFocusChange: (value) => setState(() => focused = value),
      onKeyEvent: (_, event) {
        if (event is! KeyDownEvent) return KeyEventResult.ignored;
        if (event.logicalKey == LogicalKeyboardKey.arrowLeft) {
          widget.onDrag(-16);
        } else if (event.logicalKey == LogicalKeyboardKey.arrowRight) {
          widget.onDrag(16);
        } else {
          return KeyEventResult.ignored;
        }
        return KeyEventResult.handled;
      },
      child: MouseRegion(
        cursor: SystemMouseCursors.resizeColumn,
        onEnter: (_) => setState(() => hovered = true),
        onExit: (_) => setState(() => hovered = false),
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onHorizontalDragUpdate: (e) => widget.onDrag(e.delta.dx),
          child: SizedBox(
            width: 24,
            child: Center(
              child: SizedBox(
                width: focused || hovered ? 2 : 1,
                height: double.infinity,
                child: ColoredBox(
                  color: focused || hovered ? Palette.accent : Palette.line,
                ),
              ),
            ),
          ),
        ),
      ),
    ),
  );
}

class _CameraHeader extends StatelessWidget {
  const _CameraHeader({required this.model});
  final OperatorController model;
  @override
  Widget build(BuildContext context) =>
      SectionTitle(model.snapshot?.camera.name ?? 'Camera');
}

class FollowControls extends StatelessWidget {
  const FollowControls({
    super.key,
    required this.model,
    this.choosePerson = false,
    this.desktop = false,
  });
  final OperatorController model;
  final bool choosePerson, desktop;
  @override
  Widget build(BuildContext context) {
    final person = model.selectedPerson;
    final follow = model.followAvailability;
    final land = model.availability(Capability.landCurrent, newMission: true);
    final point = model.availability(Capability.landPoint, newMission: true);
    final tag = model.availability(Capability.landTag, newMission: true);
    final start = FilledButton.icon(
      onPressed: follow.available ? model.follow : null,
      icon: const Icon(Icons.near_me_outlined, size: 18),
      label: const Text('Start following'),
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Follow target',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  const SizedBox(height: 6),
                  Text(
                    person?.name ?? 'No person selected',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  if (person != null) ...[
                    const SizedBox(height: 4),
                    Text(
                      '${person.tagLabel} · ${person.stateLabel}',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ],
              ),
            ),
            if (choosePerson)
              OutlinedButton.icon(
                onPressed: model.rosterLocked
                    ? null
                    : () => showRoster(context, model),
                icon: const Icon(Icons.people_outline, size: 18),
                label: const Text('Select person'),
              ),
            if (desktop && !choosePerson && !model.rosterLocked) ...[
              const SizedBox(width: 16),
              start,
            ],
          ],
        ),
        if ((!desktop || choosePerson) && !model.rosterLocked) ...[
          const SizedBox(height: 16),
          SizedBox(width: desktop ? null : double.infinity, child: start),
        ],
        if (!model.rosterLocked && !follow.available)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              follow.reason ?? 'Following unavailable',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            OutlinedButton.icon(
              onPressed: land.available
                  ? () => showLanding(context, model)
                  : null,
              icon: const Icon(Icons.flight_land, size: 18),
              label: const Text('Land here'),
            ),
            if (point.supported || tag.supported)
              TextButton(
                onPressed:
                    model.cameraFresh && (point.available || tag.available)
                    ? () => showLanding(context, model, pointMode: true)
                    : null,
                child: const Text('Choose landing point'),
              ),
          ],
        ),
        if (!land.available && model.snapshot != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              land.reason ?? 'Landing unavailable',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
      ],
    );
  }
}

class MissionPanel extends StatelessWidget {
  const MissionPanel({super.key, required this.model});
  final OperatorController model;
  @override
  Widget build(BuildContext context) {
    final state = model.snapshot?.mission;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SectionTitle('Mission'),
        const SizedBox(height: 12),
        Semantics(
          liveRegion: true,
          child: Text(
            model.missionLabel,
            style: Theme.of(context).textTheme.titleLarge,
          ),
        ),
        if (state?.progress != null) ...[
          const SizedBox(height: 16),
          LinearProgressIndicator(
            value: state!.progress,
            color: Palette.accent,
          ),
        ],
        if (state?.reason != null)
          Notice(state!.reason!, error: state.phase == 'failed'),
        if (model.taskMessage != null)
          Notice(
            model.taskMessage!,
            error: model.unknownRequest != null || state?.phase == 'failed',
          ),
        if (model.unknownRequest != null)
          TextButton.icon(
            onPressed: model.reconcile,
            icon: const Icon(Icons.refresh, size: 18),
            label: const Text('Refresh mission status'),
          ),
        if (model.canStop || model.canAbort) ...[
          const SizedBox(height: 16),
          if (model.canStop)
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                onPressed: model.stop,
                child: const Text('Stop following'),
              ),
            ),
          if (model.canAbort)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: SizedBox(
                width: double.infinity,
                child: OutlinedButton(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Palette.danger,
                  ),
                  onPressed: () => showAbort(context, model),
                  child: const Text('Abort mission'),
                ),
              ),
            ),
        ],
      ],
    );
  }
}
