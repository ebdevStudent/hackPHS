import 'package:flutter/material.dart';

abstract final class Palette {
  static const page = Color(0xFFF6F7F4), surface = Color(0xFFFFFFFF);
  static const ink = Color(0xFF202824), secondary = Color(0xFF657069);
  static const line = Color(0xFFDDE3DC), accent = Color(0xFF295D4D);
  static const selected = Color(0xFFE8F0EA), video = Color(0xFF111B18);
  static const warning = Color(0xFF805719), danger = Color(0xFFAD3535);
}

ThemeData operatorTheme(bool compact) {
  final size = compact ? 16.0 : 14.0;
  final base = TextStyle(
    fontFamily: 'Inter',
    color: Palette.ink,
    fontSize: size,
    height: 1.45,
    fontFeatures: const [FontFeature.tabularFigures()],
  );
  final scheme = ColorScheme.fromSeed(seedColor: Palette.accent).copyWith(
    primary: Palette.accent,
    onPrimary: Colors.white,
    surface: Palette.surface,
    onSurface: Palette.ink,
    onSurfaceVariant: Palette.secondary,
    error: Palette.danger,
    outline: Palette.line,
    surfaceTint: Colors.transparent,
  );
  ButtonStyle button({bool outlined = false}) => ButtonStyle(
    minimumSize: const WidgetStatePropertyAll(Size(48, 48)),
    padding: const WidgetStatePropertyAll(
      EdgeInsets.symmetric(horizontal: 16, vertical: 12),
    ),
    shape: WidgetStatePropertyAll(
      RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
    ),
    textStyle: WidgetStatePropertyAll(
      base.copyWith(fontWeight: FontWeight.w600),
    ),
    foregroundColor: WidgetStateProperty.resolveWith(
      (s) => s.contains(WidgetState.disabled)
          ? Palette.secondary
          : outlined
          ? Palette.accent
          : Colors.white,
    ),
    backgroundColor: outlined
        ? null
        : WidgetStateProperty.resolveWith(
            (s) => s.contains(WidgetState.disabled)
                ? Palette.line
                : Palette.accent,
          ),
    side: WidgetStateProperty.resolveWith(
      (s) => BorderSide(
        color: s.contains(WidgetState.focused)
            ? Palette.accent
            : outlined
            ? Palette.line
            : Colors.transparent,
        width: s.contains(WidgetState.focused) ? 2 : 1,
      ),
    ),
  );
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    fontFamily: 'Inter',
    scaffoldBackgroundColor: Palette.page,
    canvasColor: Palette.surface,
    textTheme: TextTheme(
      headlineSmall: base.copyWith(
        fontSize: compact ? 24 : 28,
        fontWeight: FontWeight.w600,
        height: 1.25,
      ),
      titleLarge: base.copyWith(fontSize: 20, fontWeight: FontWeight.w600),
      titleMedium: base.copyWith(
        fontSize: compact ? 17 : 15,
        fontWeight: FontWeight.w600,
      ),
      bodyLarge: base,
      bodyMedium: base,
      bodySmall: base.copyWith(
        fontSize: compact ? 13 : 12,
        color: Palette.secondary,
      ),
      labelLarge: base.copyWith(fontWeight: FontWeight.w600),
      labelMedium: base.copyWith(
        fontSize: compact ? 13 : 12,
        color: Palette.secondary,
      ),
    ),
    dividerColor: Palette.line,
    filledButtonTheme: FilledButtonThemeData(style: button()),
    outlinedButtonTheme: OutlinedButtonThemeData(style: button(outlined: true)),
    textButtonTheme: TextButtonThemeData(
      style: button(outlined: true)
          .copyWith(side: const WidgetStatePropertyAll(BorderSide.none)),
    ),
    iconButtonTheme: IconButtonThemeData(
      style: ButtonStyle(
        minimumSize: const WidgetStatePropertyAll(Size(48, 48)),
        foregroundColor: const WidgetStatePropertyAll(Palette.secondary),
        shape: WidgetStatePropertyAll(
          RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
        ),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Palette.surface,
      floatingLabelBehavior: FloatingLabelBehavior.always,
      contentPadding: const EdgeInsets.all(16),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(6),
        borderSide: const BorderSide(color: Palette.line),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(6),
        borderSide: const BorderSide(color: Palette.line),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(6),
        borderSide: const BorderSide(color: Palette.accent, width: 2),
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      height: 72,
      backgroundColor: Palette.surface,
      indicatorColor: Palette.selected,
      indicatorShape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(6),
      ),
      labelTextStyle: WidgetStatePropertyAll(
        base.copyWith(fontSize: 12, fontWeight: FontWeight.w500),
      ),
    ),
    bottomSheetTheme: const BottomSheetThemeData(
      backgroundColor: Palette.surface,
      showDragHandle: true,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
    ),
    dialogTheme: DialogThemeData(
      backgroundColor: Palette.surface,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
    ),
    tooltipTheme: const TooltipThemeData(
      waitDuration: Duration(milliseconds: 500),
    ),
  );
}
