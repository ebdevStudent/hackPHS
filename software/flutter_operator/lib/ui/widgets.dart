import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../application/operator_controller.dart';
import '../domain/models.dart';
import 'theme.dart';

class DroneMark extends StatelessWidget {
  const DroneMark({super.key, this.size = 28});
  final double size;
  @override
  Widget build(BuildContext context) => SizedBox.square(
    dimension: size,
    child: CustomPaint(painter: _DroneMarkPainter()),
  );
}

class _DroneMarkPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Palette.accent
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.7;
    final rect = Rect.fromLTWH(2, 2, size.width - 4, size.height - 4);
    canvas.drawOval(rect, paint);
    canvas.drawOval(
      Rect.fromCenter(
        center: rect.center,
        width: rect.width * .43,
        height: rect.height,
      ),
      paint,
    );
    canvas.save();
    canvas.translate(rect.center.dx, rect.center.dy);
    canvas.rotate(math.pi / 4);
    canvas.drawOval(
      Rect.fromCenter(
        center: Offset.zero,
        width: rect.width * .45,
        height: rect.height,
      ),
      paint,
    );
    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class StatusText extends StatelessWidget {
  const StatusText(
    this.label, {
    super.key,
    this.tone = 'neutral',
    this.small = false,
  });
  final String label, tone;
  final bool small;
  @override
  Widget build(BuildContext context) {
    final color = switch (tone) {
      'ready' => Palette.accent,
      'error' => Palette.danger,
      'warning' => Palette.warning,
      _ => Palette.secondary,
    };
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 6,
          height: 6,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 8),
        Flexible(
          child: Text(
            label,
            style:
                (small
                        ? Theme.of(context).textTheme.bodySmall
                        : Theme.of(context).textTheme.bodyMedium)
                    ?.copyWith(color: color),
          ),
        ),
      ],
    );
  }
}

class Notice extends StatelessWidget {
  const Notice(this.message, {super.key, this.error = false, this.action});
  final String message;
  final bool error;
  final Widget? action;
  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.symmetric(vertical: 12),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(top: 2),
          child: Icon(
            error ? Icons.error_outline : Icons.info_outline,
            size: 18,
            color: error ? Palette.danger : Palette.secondary,
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            message,
            style: Theme.of(context).textTheme.bodyMedium
                ?.copyWith(color: error ? Palette.danger : Palette.secondary),
          ),
        ),
        ?action,
      ],
    ),
  );
}

class EmptyState extends StatelessWidget {
  const EmptyState(
    this.title, {
    super.key,
    this.detail,
    this.icon = Icons.inbox_outlined,
  });
  final String title;
  final String? detail;
  final IconData icon;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 24),
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 28, color: Palette.secondary),
        const SizedBox(height: 12),
        Text(
          title,
          style: Theme.of(context).textTheme.titleMedium,
          textAlign: TextAlign.center,
        ),
        if (detail != null) ...[
          const SizedBox(height: 4),
          Text(
            detail!,
            style: Theme.of(context).textTheme.bodySmall,
            textAlign: TextAlign.center,
          ),
        ],
      ],
    ),
  );
}

class SectionTitle extends StatelessWidget {
  const SectionTitle(this.title, {super.key, this.trailing});
  final String title;
  final Widget? trailing;
  @override
  Widget build(BuildContext context) => Row(
    children: [
      Expanded(
        child: Text(title, style: Theme.of(context).textTheme.titleMedium),
      ),
      ?trailing,
    ],
  );
}

String ageLabel(DateTime time, DateTime now) {
  final seconds = now.difference(time).inMilliseconds / 1000;
  if (seconds < 1) return 'just now';
  if (seconds < 60) return '${seconds.floor()} s ago';
  if (seconds < 3600) return '${(seconds / 60).floor()} min ago';
  return '${(seconds / 3600).floor()} h ago';
}

String clockLabel(DateTime time) {
  final t = time.toLocal();
  return '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}:${t.second.toString().padLeft(2, '0')}';
}

class RosterList extends StatelessWidget {
  const RosterList({
    super.key,
    required this.model,
    this.onSelected,
    this.compact = false,
  });
  final OperatorController model;
  final VoidCallback? onSelected;
  final bool compact;
  @override
  Widget build(BuildContext context) {
    final roster = model.snapshot?.roster ?? <RosterPerson>[];
    if (roster.isEmpty) {
      return EmptyState(
        model.phase == LinkPhase.connecting
            ? 'Loading roster…'
            : 'No people available',
        detail: model.snapshot == null
            ? 'Connect a server to load the roster.'
            : 'The server has not supplied a roster.',
        icon: Icons.people_outline,
      );
    }
    return Column(
      children: [
        for (final person in roster)
          Padding(
            padding: const EdgeInsets.only(bottom: 4),
            child: Semantics(
              selected: person.id == model.selectedPersonId,
              button: true,
              child: Material(
                color: person.id == model.selectedPersonId
                    ? Palette.selected
                    : Colors.transparent,
                borderRadius: BorderRadius.circular(6),
                child: InkWell(
                  borderRadius: BorderRadius.circular(6),
                  onTap: model.rosterLocked
                      ? null
                      : () {
                          model.selectPerson(person.id);
                          onSelected?.call();
                        },
                  child: ConstrainedBox(
                    constraints: BoxConstraints(minHeight: compact ? 68 : 64),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 12,
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  person.name,
                                  style: Theme.of(context).textTheme.bodyMedium
                                      ?.copyWith(fontWeight: FontWeight.w600),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  '${person.tagLabel} · ${person.stateLabel}',
                                  style: Theme.of(context).textTheme.bodySmall,
                                ),
                              ],
                            ),
                          ),
                          if (person.id == model.selectedPersonId)
                            const Padding(
                              padding: EdgeInsets.only(top: 3),
                              child: Icon(
                                Icons.check,
                                size: 18,
                                color: Palette.accent,
                              ),
                            ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        if (model.rosterLocked)
          const Notice('Stop the current task to change person.'),
      ],
    );
  }
}

Future<void> showRoster(BuildContext context, OperatorController model) async {
  final compact = MediaQuery.sizeOf(context).width < 680;
  Widget content(BuildContext c) => AnimatedBuilder(
    animation: model,
    builder: (c, _) => Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          SectionTitle(
            'Select person',
            trailing: IconButton(
              tooltip: 'Close',
              onPressed: () => Navigator.pop(c),
              icon: const Icon(Icons.close),
            ),
          ),
          const SizedBox(height: 12),
          Flexible(
            child: SingleChildScrollView(
              child: RosterList(
                model: model,
                compact: compact,
                onSelected: () => Navigator.pop(c),
              ),
            ),
          ),
        ],
      ),
    ),
  );
  if (compact) {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      sheetAnimationStyle: MediaQuery.disableAnimationsOf(context)
          ? AnimationStyle.noAnimation
          : null,
      useSafeArea: true,
      constraints: BoxConstraints(
        maxHeight: MediaQuery.sizeOf(context).height * .8,
      ),
      builder: content,
    );
  } else {
    await showDialog<void>(
      context: context,
      animationStyle: MediaQuery.disableAnimationsOf(context)
          ? AnimationStyle.noAnimation
          : null,
      builder: (c) => Dialog(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 440, maxHeight: 650),
          child: content(c),
        ),
      ),
    );
  }
}

class EventList extends StatelessWidget {
  const EventList({super.key, required this.model, this.limit = 6});
  final OperatorController model;
  final int limit;
  @override
  Widget build(BuildContext context) {
    final events = model.snapshot?.events ?? <BackendEvent>[];
    if (events.isEmpty) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 16),
        child: Text(
          'No recent events',
          style: TextStyle(color: Palette.secondary),
        ),
      );
    }
    return Column(
      children: [
        for (final event in events.take(limit))
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 10),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: const EdgeInsets.only(top: 5),
                  child: Container(
                    width: 5,
                    height: 5,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: event.severity == 'error'
                          ? Palette.danger
                          : event.severity == 'warning'
                          ? Palette.warning
                          : Palette.secondary,
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(event.message),
                      const SizedBox(height: 4),
                      Tooltip(
                        message: clockLabel(event.time),
                        child: Text(
                          ageLabel(event.time, model.now),
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class BusyLabel extends StatelessWidget {
  const BusyLabel(this.text, {super.key, required this.busy});
  final String text;
  final bool busy;
  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      if (busy) ...[
        const SizedBox.square(
          dimension: 16,
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
        const SizedBox(width: 10),
      ],
      Flexible(child: Text(text)),
    ],
  );
}
