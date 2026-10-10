import 'dart:math' as math;
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_webrtc/flutter_webrtc.dart';

import '../application/operator_controller.dart';
import '../domain/landing_geometry.dart';
import '../domain/models.dart';
import 'theme.dart';
import 'widgets.dart';

class CameraViewport extends StatelessWidget {
  const CameraViewport({
    super.key,
    required this.model,
    this.still,
    this.point,
    this.onPoint,
    this.drawTags = true,
  });
  final OperatorController model;
  final CapturedFrame? still;
  final NormalizedPoint? point;
  final ValueChanged<NormalizedPoint>? onPoint;
  final bool drawTags;
  @override
  Widget build(BuildContext context) {
    final frame =
        still?.metadata ?? model.displayedFrame ?? model.snapshot?.camera.frame;
    final bytes = still?.bytes ?? model.frameBytes;
    final renderer = still == null ? model.media.renderer : null;
    final isFresh = still != null
        ? still!.metadata.isFresh(model.now)
        : model.cameraFresh;
    final hasRtc =
        renderer != null && renderer.value.width > 0 && model.media.ready;
    final source = model.snapshot?.source == 'mock' ? 'Mock source' : 'Live';
    final hasImage = bytes != null && frame != null;
    final available = hasImage || hasRtc;
    return Semantics(
      label: still != null ? 'Captured camera frame' : 'Camera viewport',
      child: AspectRatio(
        aspectRatio: frame?.aspectRatio ?? 16 / 9,
        child: ClipRRect(
          borderRadius: BorderRadius.circular(10),
          child: ColoredBox(
            color: Palette.video,
            child: Stack(
              fit: StackFit.expand,
              children: [
                if (hasRtc)
                  RTCVideoView(
                    renderer,
                    objectFit:
                        RTCVideoViewObjectFit.RTCVideoViewObjectFitContain,
                  )
                else if (hasImage)
                  _frameImage(frame, bytes)
                else
                  Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(
                            Icons.videocam_off_outlined,
                            size: 32,
                            color: Color(0xFF96ABA1),
                          ),
                          const SizedBox(height: 12),
                          const Text(
                            'Camera offline',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 17,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            model.connected
                                ? 'Waiting for a camera stream.'
                                : 'Connect a server to view the camera.',
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              color: Color(0xFFBAC8C0),
                              fontSize: 13,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                if (available && frame != null && drawTags && isFresh)
                  IgnorePointer(
                    child: CustomPaint(
                      painter: _TrackingPainter(
                        frame,
                        model.snapshot?.roster ?? [],
                      ),
                    ),
                  ),
                if (onPoint != null && frame != null)
                  Positioned.fill(
                    child: GestureDetector(
                      behavior: HitTestBehavior.opaque,
                      onTapDown: (e) {
                        final box = context.findRenderObject() as RenderBox?;
                        if (box == null) return;
                        // AspectRatio fixes the image rectangle; no letterbox pixels are selectable.
                        final p = NormalizedPoint(
                          e.localPosition.dx / box.size.width,
                          e.localPosition.dy / box.size.height,
                        );
                        if (p.valid) onPoint!(p);
                      },
                    ),
                  ),
                if (point != null)
                  Positioned.fill(
                    child: IgnorePointer(
                      child: CustomPaint(painter: _LandingPainter(point!)),
                    ),
                  ),
                if (available)
                  Positioned(
                    top: 12,
                    left: 12,
                    child: _OverlayLabel(
                      still != null
                          ? 'Captured frame'
                          : isFresh
                          ? source
                          : 'Video stale',
                      warning: !isFresh || model.snapshot?.source == 'mock',
                    ),
                  ),
                if (available && frame != null)
                  Positioned(
                    top: 12,
                    right: 12,
                    child: _OverlayLabel(ageLabel(frame.capturedAt, model.now)),
                  ),
                if (available && !isFresh)
                  const Positioned(
                    left: 16,
                    right: 16,
                    bottom: 16,
                    child: _OverlayLabel('Frame expired', warning: true),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _frameImage(CameraFrame frame, Uint8List bytes) {
    Widget image = Image.memory(
      bytes,
      gaplessPlayback: true,
      fit: BoxFit.fill,
      errorBuilder: (_, _, _) => const Center(
        child: Text(
          'Camera frame unavailable',
          style: TextStyle(color: Colors.white),
        ),
      ),
    );
    if (frame.mirrored) image = Transform.flip(flipX: true, child: image);
    return RotatedBox(quarterTurns: frame.rotation ~/ 90, child: image);
  }
}

class _OverlayLabel extends StatelessWidget {
  const _OverlayLabel(this.label, {this.warning = false});
  final String label;
  final bool warning;
  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      color: Palette.video.withValues(alpha: .90),
      borderRadius: BorderRadius.circular(4),
    ),
    child: Padding(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
      child: Text(
        label,
        style: TextStyle(
          color: warning ? const Color(0xFFF3D6A4) : Colors.white,
          fontSize: 12,
          height: 1.2,
        ),
      ),
    ),
  );
}

class _TrackingPainter extends CustomPainter {
  _TrackingPainter(this.frame, this.roster);
  final CameraFrame frame;
  final List<RosterPerson> roster;
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0xFFAFE0B9)
      ..strokeWidth = 1.5
      ..style = PaintingStyle.stroke;
    for (final tag in frame.tags) {
      final corners = [
        toDisplayPoint(frame, NormalizedPoint(tag.bounds.x, tag.bounds.y)),
        toDisplayPoint(
          frame,
          NormalizedPoint(
            tag.bounds.x + tag.bounds.width,
            tag.bounds.y + tag.bounds.height,
          ),
        ),
      ];
      final left = math.min(corners[0].x, corners[1].x) * size.width;
      final top = math.min(corners[0].y, corners[1].y) * size.height;
      final right = math.max(corners[0].x, corners[1].x) * size.width;
      final bottom = math.max(corners[0].y, corners[1].y) * size.height;
      final rect = Rect.fromLTRB(
        left,
        top,
        right,
        bottom,
      ).intersect(Offset.zero & size);
      if (rect.isEmpty) continue;
      canvas.drawRRect(
        RRect.fromRectAndRadius(rect, const Radius.circular(3)),
        paint,
      );
      String name = 'Tag ${tag.tagId}';
      for (final person in roster) {
        if (person.id == tag.personId) {
          name = '${person.name} · ${person.tagLabel}';
        }
      }
      final text = TextPainter(
        text: TextSpan(
          text: name,
          style: const TextStyle(
            fontFamily: 'Inter',
            fontSize: 11,
            color: Color(0xFFAFE0B9),
            fontWeight: FontWeight.w500,
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout(maxWidth: math.max(50, size.width - 24));
      final y = math.max(45, top - text.height - 12).toDouble();
      final x = left.clamp(8, size.width - text.width - 16).toDouble();
      canvas.drawRRect(
        RRect.fromRectAndRadius(
          Rect.fromLTWH(x, y, text.width + 12, text.height + 8),
          const Radius.circular(3),
        ),
        Paint()..color = Palette.video.withValues(alpha: .95),
      );
      text.paint(canvas, Offset(x + 6, y + 4));
    }
  }

  @override
  bool shouldRepaint(covariant _TrackingPainter old) =>
      old.frame.id != frame.id;
}

class _LandingPainter extends CustomPainter {
  _LandingPainter(this.point);
  final NormalizedPoint point;
  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(point.x * size.width, point.y * size.height);
    final paint = Paint()
      ..color = Colors.white
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;
    canvas.drawCircle(center, 13, paint);
    canvas.drawCircle(center, 3, Paint()..color = Palette.accent);
    canvas.drawLine(
      center + const Offset(-22, 0),
      center + const Offset(-10, 0),
      paint,
    );
    canvas.drawLine(
      center + const Offset(10, 0),
      center + const Offset(22, 0),
      paint,
    );
    canvas.drawLine(
      center + const Offset(0, -22),
      center + const Offset(0, -10),
      paint,
    );
    canvas.drawLine(
      center + const Offset(0, 10),
      center + const Offset(0, 22),
      paint,
    );
  }

  @override
  bool shouldRepaint(covariant _LandingPainter old) =>
      old.point.x != point.x || old.point.y != point.y;
}
