import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../application/operator_controller.dart';
import '../domain/models.dart';
import 'theme.dart';
import 'widgets.dart';

class TalkButton extends StatefulWidget {
  const TalkButton({super.key, required this.model, this.small = false});
  final OperatorController model;
  final bool small;
  @override
  State<TalkButton> createState() => _TalkButtonState();
}

class _TalkButtonState extends State<TalkButton> {
  bool focused = false, hovered = false;
  @override
  Widget build(BuildContext context) {
    final m = widget.model;
    final enabled =
        m.availability(Capability.audioTransmit).available &&
        m.media.microphoneReady &&
        m.media.ready;
    final active = m.transmitting;
    return Semantics(
      button: true,
      enabled: enabled,
      label: 'Hold to talk',
      value: active
          ? 'Transmitting'
          : m.talkHeld
          ? 'Connecting microphone'
          : 'Ready',
      onTap: enabled
          ? () {
              if (m.talkHeld) {
                m.endTalk();
              } else {
                unawaited(m.startTalk());
              }
            }
          : null,
      excludeSemantics: true,
      child: Focus(
        onFocusChange: (v) {
          setState(() => focused = v);
          if (!v) m.endTalk();
        },
        onKeyEvent: (_, event) {
          if (!enabled ||
              (event.logicalKey != LogicalKeyboardKey.space &&
                  event.logicalKey != LogicalKeyboardKey.enter)) {
            return KeyEventResult.ignored;
          }
          if (event is KeyDownEvent) unawaited(m.startTalk());
          if (event is KeyUpEvent) m.endTalk();
          return KeyEventResult.handled;
        },
        child: MouseRegion(
          cursor: enabled ? SystemMouseCursors.click : SystemMouseCursors.basic,
          onEnter: (_) => setState(() => hovered = true),
          onExit: (_) {
            setState(() => hovered = false);
            m.endTalk();
          },
          child: GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTapDown: enabled ? (_) => unawaited(m.startTalk()) : null,
            onTapUp: enabled ? (_) => m.endTalk() : null,
            onTapCancel: m.endTalk,
            child: AnimatedContainer(
              duration: MediaQuery.disableAnimationsOf(context)
                  ? Duration.zero
                  : const Duration(milliseconds: 120),
              constraints: BoxConstraints(minHeight: widget.small ? 48 : 72),
              padding: EdgeInsets.symmetric(
                horizontal: widget.small ? 16 : 20,
                vertical: widget.small ? 12 : 20,
              ),
              decoration: BoxDecoration(
                color: active
                    ? Palette.accent
                    : enabled
                    ? (hovered ? const Color(0xFFDCE9DE) : Palette.selected)
                    : Palette.page,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(
                  color: focused ? Palette.accent : Palette.line,
                  width: focused ? 2 : 1,
                ),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    active ? Icons.mic : Icons.mic_none_outlined,
                    size: 20,
                    color: active
                        ? Colors.white
                        : enabled
                        ? Palette.accent
                        : Palette.secondary,
                  ),
                  const SizedBox(width: 10),
                  Flexible(
                    child: Text(
                      active ? 'Talking…' : 'Hold to talk',
                      style: TextStyle(
                        color: active
                            ? Colors.white
                            : enabled
                            ? Palette.accent
                            : Palette.secondary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class AudioDock extends StatelessWidget {
  const AudioDock({super.key, required this.model});
  final OperatorController model;
  @override
  Widget build(BuildContext context) {
    final receive = model.availability(Capability.audioReceive);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 8,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            TextButton(
              onPressed: () => model.navigate(1),
              child: const Text('Open audio'),
            ),
            OutlinedButton.icon(
              onPressed: receive.available && model.media.ready
                  ? model.toggleListening
                  : null,
              icon: Icon(
                model.media.listening
                    ? Icons.volume_up_outlined
                    : Icons.volume_off_outlined,
                size: 18,
              ),
              label: Text(model.media.listening ? 'Mute' : 'Listen'),
            ),
            if (model.media.microphoneReady)
              TalkButton(model: model, small: true)
            else
              TextButton.icon(
                onPressed:
                    model.availability(Capability.audioTransmit).available &&
                        model.media.ready
                    ? model.enableMicrophone
                    : null,
                icon: const Icon(Icons.mic_none_outlined, size: 18),
                label: const Text('Enable microphone'),
              ),
          ],
        ),
      ],
    );
  }
}

class AudioView extends StatelessWidget {
  const AudioView({super.key, required this.model, required this.compact});
  final OperatorController model;
  final bool compact;
  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final controls = Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionTitle('Incoming audio'),
          const SizedBox(height: 16),
          Row(
            children: [
              const Icon(
                Icons.volume_up_outlined,
                size: 22,
                color: Palette.secondary,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  model.media.listening
                      ? model.isFixture
                            ? 'Listening · fixture'
                            : 'Listening'
                      : 'Muted',
                ),
              ),
              OutlinedButton(
                onPressed:
                    model.availability(Capability.audioReceive).available &&
                        model.media.ready
                    ? model.toggleListening
                    : null,
                child: Text(model.media.listening ? 'Mute' : 'Listen'),
              ),
            ],
          ),
          if (!model.availability(Capability.audioReceive).available)
            Notice(
              model.availability(Capability.audioReceive).reason ??
                  'Audio unavailable',
            ),
          const SizedBox(height: 28),
          const Divider(height: 1),
          const SizedBox(height: 24),
          const SectionTitle('Microphone'),
          const SizedBox(height: 12),
          Text(
            model.transmitting
                ? 'Transmitting'
                : model.microphonePending
                ? 'Requesting microphone permission…'
                : model.media.microphoneReady
                ? model.isFixture
                      ? 'Enabled · fixture'
                      : 'Enabled'
                : 'Not enabled',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 16),
          if (!model.media.microphoneReady) ...[
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed:
                    model.availability(Capability.audioTransmit).available &&
                        model.media.ready &&
                        !model.microphonePending
                    ? model.enableMicrophone
                    : null,
                icon: const Icon(Icons.mic_none_outlined, size: 18),
                label: BusyLabel(
                  'Enable microphone',
                  busy: model.microphonePending,
                ),
              ),
            ),
            const SizedBox(height: 12),
          ],
          SizedBox(
            width: double.infinity,
            child: TalkButton(model: model),
          ),
          if (!model.availability(Capability.audioTransmit).available)
            Notice(
              model.availability(Capability.audioTransmit).reason ??
                  'Microphone unavailable',
            ),
          if (model.media.error != null) ...[
            Notice(model.media.error!, error: true),
            Wrap(
              spacing: 8,
              children: [
                TextButton(
                  onPressed: model.retryMedia,
                  child: const Text('Reconnect media'),
                ),
                if (model.media.error!.contains('permission'))
                  TextButton(
                    onPressed: () => _settings(context),
                    child: const Text('Open settings'),
                  ),
              ],
            ),
          ],
        ],
      );
      final speech = SpeechComposer(model: model);
      return SingleChildScrollView(
        key: const PageStorageKey('audio-scroll'),
        padding: EdgeInsets.all(compact ? 16 : 24),
        child: Align(
          alignment: Alignment.topLeft,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1120),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                StatusText(
                  model.snapshot == null
                      ? 'Audio unavailable'
                      : model.snapshot!.audio.state == 'ready'
                      ? model.isFixture
                            ? 'Audio fixture ready'
                            : 'Audio node ready'
                      : 'Audio unavailable',
                  tone: model.snapshot?.audio.state == 'ready'
                      ? 'neutral'
                      : 'warning',
                ),
                if (model.snapshot?.audio.reason != null)
                  Notice(model.snapshot!.audio.reason!),
                const SizedBox(height: 28),
                if (constraints.maxWidth >= 920)
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(width: 320, child: controls),
                      const SizedBox(width: 40),
                      Expanded(child: speech),
                    ],
                  )
                else
                  Column(
                    children: [
                      controls,
                      const SizedBox(height: 28),
                      const Divider(height: 1),
                      const SizedBox(height: 24),
                      speech,
                    ],
                  ),
              ],
            ),
          ),
        ),
      );
    },
  );
  Future<void> _settings(BuildContext context) async {
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      try {
        await const MethodChannel('ball_drone/settings')
            .invokeMethod<void>('openAppSettings');
        return;
      } catch (_) {}
    }
    if (context.mounted) {
      await showDialog<void>(
        context: context,
        builder: (c) => AlertDialog(
          title: const Text('Microphone settings'),
          content: Text(
            kIsWeb
                ? 'Allow microphone access in your browser’s site settings, then choose Enable microphone.'
                : 'Allow microphone access for Ball Drone in system settings, then choose Enable microphone.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(c),
              child: const Text('Close'),
            ),
          ],
        ),
      );
    }
  }
}

class SpeechComposer extends StatelessWidget {
  const SpeechComposer({super.key, required this.model});
  final OperatorController model;
  @override
  Widget build(BuildContext context) {
    final audio = model.snapshot?.audio,
        availability = model.availability(Capability.tts);
    final max = audio?.maxTextLength ?? 500,
        count = model.draft.text.trim().runes.length;
    final valid = count > 0 && count <= max;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SectionTitle('Text to speech'),
        const SizedBox(height: 20),
        if ((audio?.voices.length ?? 0) > 1) ...[
          DropdownButtonFormField<String>(
            initialValue: model.voiceId,
            decoration: const InputDecoration(labelText: 'Voice'),
            items: audio!.voices
                .map((v) => DropdownMenuItem(value: v.id, child: Text(v.name)))
                .toList(),
            onChanged: (v) => model.setVoice(v),
          ),
          const SizedBox(height: 20),
        ] else if (audio?.voices.length == 1) ...[
          Text(
            'Voice · ${audio!.voices.first.name}',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 12),
        ],
        TextField(
          key: const ValueKey('tts-draft'),
          controller: model.draft,
          minLines: 5,
          maxLines: 8,
          keyboardType: TextInputType.multiline,
          maxLength: 2000,
          maxLengthEnforcement: MaxLengthEnforcement.none,
          decoration: InputDecoration(
            labelText: 'Text to speak',
            counterText: '$count / $max',
            errorText: count > max ? 'Text exceeds the server’s limit.' : null,
          ),
          scrollPadding: const EdgeInsets.all(80),
        ),
        const SizedBox(height: 16),
        FilledButton.icon(
          onPressed:
              availability.available &&
                  valid &&
                  !model.speechPending &&
                  model.unknownSpeechRequest == null
              ? model.speak
              : null,
          icon: const Icon(Icons.volume_up_outlined, size: 18),
          label: BusyLabel('Speak', busy: model.speechPending),
        ),
        if (!availability.available)
          Notice(availability.reason ?? 'Text to speech unavailable'),
        if (model.audioMessage != null)
          Notice(
            model.audioMessage!,
            error: model.unknownSpeechRequest != null,
          ),
        if (model.unknownSpeechRequest != null)
          TextButton.icon(
            onPressed: model.reconcileSpeech,
            icon: const Icon(Icons.refresh, size: 18),
            label: const Text('Refresh playback status'),
          ),
        if (audio?.speech.isNotEmpty == true) ...[
          const SizedBox(height: 24),
          const Divider(height: 1),
          const SizedBox(height: 24),
          const SectionTitle('Playback'),
          const SizedBox(height: 8),
          for (final item in audio!.speech)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(item.text, maxLines: 3, overflow: TextOverflow.ellipsis),
                  const SizedBox(height: 6),
                  StatusText(
                    item.state[0].toUpperCase() + item.state.substring(1),
                    small: true,
                    tone: item.state == 'failed' || item.state == 'rejected'
                        ? 'error'
                        : 'neutral',
                  ),
                  if (item.reason != null) Notice(item.reason!, error: true),
                ],
              ),
            ),
        ],
      ],
    );
  }
}
