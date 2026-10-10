import 'package:flutter/material.dart';

import '../application/operator_controller.dart';
import '../domain/models.dart';
import 'audio.dart';
import 'dialogs.dart';
import 'operations.dart';
import 'system.dart';
import 'theme.dart';
import 'widgets.dart';

class OperatorApp extends StatefulWidget {
  const OperatorApp({
    super.key,
    required this.controller,
    this.disposeController = true,
  });
  final OperatorController controller;
  final bool disposeController;
  @override
  State<OperatorApp> createState() => _OperatorAppState();
}

class _OperatorAppState extends State<OperatorApp> with WidgetsBindingObserver {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed) widget.controller.endTalk();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    if (widget.disposeController) widget.controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'Ball Drone',
    debugShowCheckedModeBanner: false,
    theme: operatorTheme(false),
    home: AnimatedBuilder(
      animation: widget.controller,
      builder: (context, _) => LayoutBuilder(
        builder: (context, c) {
          final m = widget.controller;
          final scale = MediaQuery.textScalerOf(context)
              .scale(1)
              .clamp(1.0, 1.5);
          final compact = c.maxWidth < 680 * scale,
              wide = c.maxWidth >= 1280 * scale;
          final content = Theme(
            data: operatorTheme(compact),
            child: Scaffold(
              body: SafeArea(
                child: Row(
                  children: [
                    if (!compact) _Sidebar(model: m, wide: wide),
                    Expanded(
                      child: Column(
                        children: [
                          _Header(model: m, compact: compact),
                          if (m.isFixture || m.snapshot?.source == 'mock')
                            Container(
                              width: double.infinity,
                              padding: const EdgeInsets.symmetric(
                                horizontal: 24,
                                vertical: 9,
                              ),
                              color: const Color(0xFFFBF3E4),
                              child: Row(
                                children: [
                                  const Icon(
                                    Icons.science_outlined,
                                    size: 16,
                                    color: Palette.warning,
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      m.sourceLabel,
                                      style: const TextStyle(
                                        fontSize: 12,
                                        color: Palette.warning,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          if (m.connectionError != null)
                            Padding(
                              padding: EdgeInsets.symmetric(
                                horizontal: compact ? 16 : 24,
                              ),
                              child: Notice(m.connectionError!, error: true),
                            ),
                          Expanded(
                            child: IndexedStack(
                              index: m.destination,
                              children: [
                                OperationsView(
                                  model: m,
                                  wide: wide,
                                  compact: compact,
                                ),
                                AudioView(model: m, compact: compact),
                                SystemView(model: m, compact: compact),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              bottomNavigationBar: compact
                  ? DecoratedBox(
                      decoration: const BoxDecoration(
                        border: Border(top: BorderSide(color: Palette.line)),
                      ),
                      child: NavigationBar(
                        selectedIndex: m.destination,
                        onDestinationSelected: m.navigate,
                        destinations: const [
                          NavigationDestination(
                            icon: Icon(Icons.videocam_outlined),
                            selectedIcon: Icon(Icons.videocam),
                            label: 'Live',
                          ),
                          NavigationDestination(
                            icon: Icon(Icons.volume_up_outlined),
                            selectedIcon: Icon(Icons.volume_up),
                            label: 'Audio',
                          ),
                          NavigationDestination(
                            icon: Icon(Icons.tune_outlined),
                            selectedIcon: Icon(Icons.tune),
                            label: 'System',
                          ),
                        ],
                      ),
                    )
                  : null,
            ),
          );
          return PopScope(
            canPop: m.destination == 0,
            onPopInvokedWithResult: (didPop, _) {
              if (!didPop) m.navigate(0);
            },
            child: content,
          );
        },
      ),
    ),
  );
}

class _Header extends StatelessWidget {
  const _Header({required this.model, required this.compact});
  final OperatorController model;
  final bool compact;
  @override
  Widget build(BuildContext context) {
    final phase = model.phase;
    final title = model.destination == 0
        ? (compact ? 'Live' : 'Operations')
        : model.destination == 1
        ? 'Audio'
        : 'System';
    final status = switch (phase) {
      LinkPhase.connected => model.fresh ? 'Connected' : 'Status stale',
      LinkPhase.connecting => 'Connecting',
      LinkPhase.reconnecting => 'Reconnecting',
      LinkPhase.unauthorized => 'Authorization required',
      LinkPhase.incompatible => 'Incompatible server',
      _ => 'Disconnected',
    };
    return Padding(
      padding: EdgeInsets.fromLTRB(
        compact ? 16 : 24,
        compact ? 20 : 24,
        compact ? 16 : 24,
        compact ? 16 : 20,
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: Theme.of(context).textTheme.headlineSmall),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 16,
                  runSpacing: 4,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    StatusText(
                      status,
                      small: true,
                      tone: model.fresh
                          ? 'ready'
                          : phase == LinkPhase.disconnected
                          ? 'neutral'
                          : 'warning',
                    ),
                    if (!compact && model.snapshot != null)
                      Text(
                        model.snapshot!.serverName,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    if (model.snapshot?.authorized == false)
                      Text(
                        'Read only',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          OutlinedButton.icon(
            onPressed: () => showConnection(context, model),
            icon: const Icon(Icons.link, size: 18),
            label: Text(model.connected ? 'Session' : 'Connect'),
          ),
        ],
      ),
    );
  }
}

class _Sidebar extends StatelessWidget {
  const _Sidebar({required this.model, required this.wide});
  final OperatorController model;
  final bool wide;
  @override
  Widget build(BuildContext context) => Container(
    width: wide ? 184 : 80,
    decoration: const BoxDecoration(
      color: Palette.surface,
      border: Border(right: BorderSide(color: Palette.line)),
    ),
    padding: EdgeInsets.symmetric(horizontal: wide ? 12 : 8, vertical: 24),
    child: Column(
      children: [
        Padding(
          padding: EdgeInsets.symmetric(horizontal: wide ? 8 : 0),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const DroneMark(),
              if (wide) ...[
                const SizedBox(width: 10),
                const Expanded(
                  child: Text(
                    'Ball Drone',
                    style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
                  ),
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 32),
        for (final entry in [
          (0, 'Operations', Icons.videocam_outlined),
          (1, 'Audio', Icons.volume_up_outlined),
          (2, 'System', Icons.tune_outlined),
        ])
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Tooltip(
              message: entry.$2,
              excludeFromSemantics: true,
              child: Material(
                color: model.destination == entry.$1
                    ? Palette.selected
                    : Colors.transparent,
                borderRadius: BorderRadius.circular(6),
                child: InkWell(
                  borderRadius: BorderRadius.circular(6),
                  onTap: () => model.navigate(entry.$1),
                  child: Semantics(
                    selected: model.destination == entry.$1,
                    button: true,
                    label: wide ? null : entry.$2,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 14,
                      ),
                      child: wide
                          ? Row(
                              children: [
                                Icon(
                                  entry.$3,
                                  size: 20,
                                  color: model.destination == entry.$1
                                      ? Palette.accent
                                      : Palette.secondary,
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Text(
                                    entry.$2,
                                    style: TextStyle(
                                      fontWeight: model.destination == entry.$1
                                          ? FontWeight.w600
                                          : FontWeight.w400,
                                    ),
                                  ),
                                ),
                              ],
                            )
                          : Icon(
                              entry.$3,
                              size: 22,
                              color: model.destination == entry.$1
                                  ? Palette.accent
                                  : Palette.secondary,
                            ),
                    ),
                  ),
                ),
              ),
            ),
          ),
      ],
    ),
  );
}
