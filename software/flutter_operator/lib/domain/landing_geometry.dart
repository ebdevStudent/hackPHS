import 'models.dart';

/// Display coordinates exclude letterboxing. Requests identify the original frame.
NormalizedPoint toSourcePoint(CameraFrame frame, NormalizedPoint displayed) {
  if (!displayed.valid) {
    throw const FormatException('Point is outside the image');
  }
  var p = switch (frame.rotation) {
    90 => NormalizedPoint(displayed.y, 1 - displayed.x),
    180 => NormalizedPoint(1 - displayed.x, 1 - displayed.y),
    270 => NormalizedPoint(1 - displayed.y, displayed.x),
    _ => displayed,
  };
  if (frame.mirrored) p = NormalizedPoint(1 - p.x, p.y);
  return NormalizedPoint(
    frame.crop.x + p.x * frame.crop.width,
    frame.crop.y + p.y * frame.crop.height,
  );
}

NormalizedPoint toDisplayPoint(CameraFrame frame, NormalizedPoint source) {
  var p = NormalizedPoint(
    (source.x - frame.crop.x) / frame.crop.width,
    (source.y - frame.crop.y) / frame.crop.height,
  );
  if (frame.mirrored) p = NormalizedPoint(1 - p.x, p.y);
  return switch (frame.rotation) {
    90 => NormalizedPoint(1 - p.y, p.x),
    180 => NormalizedPoint(1 - p.x, 1 - p.y),
    270 => NormalizedPoint(p.y, 1 - p.x),
    _ => p,
  };
}
