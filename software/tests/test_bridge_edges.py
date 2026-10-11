"""Serial framing/ACK validation with an in-memory device, not a physical port."""
import pytest
from ball_demo import bridge as module
from ball_demo.bridge import MockBridge, SerialBridge
from ball_demo.protocol import MAX_FRAME

class Serial:
    def __init__(self, *args, **kwargs): self.incoming, self.writes, self.closed = bytearray(), [], False
    @property
    def in_waiting(self): return len(self.incoming)
    def read(self, size):
        data = bytes(self.incoming[:size]); del self.incoming[:size]; return data
    def write(self, data): self.writes.append(data); return len(data)
    def open(self): pass
    def close(self): self.closed = True

@pytest.fixture
def adapter(monkeypatch):
    monkeypatch.setattr(module.serial, 'Serial', Serial)
    bridge = SerialBridge('in-memory-only')
    yield bridge
    bridge.close()

def feed(bridge, message, now):
    bridge.serial.incoming.extend(message if isinstance(message, bytes) else message.encode())
    return bridge.poll(now)

def ready(bridge, now=1):
    feed(bridge, f'READY 1 {bridge.session} NO_OUTPUT\n', now)
    assert bridge.ready

def test_not_ready_send_is_noop_and_hello_is_sent(adapter):
    adapter.send(True, 200, 1)
    assert adapter.seq == 0 and len(adapter.serial.writes) == 1
    assert adapter.serial.writes[0] == f'HELLO 1 {adapter.session}\n'.encode()

def test_serial_port_opens_at_default_or_requested_baud(monkeypatch):
    opened = []
    class Recording(Serial):
        def __init__(self, device, baud, **kwargs): super().__init__(); opened.append(baud)
    monkeypatch.setattr(module.serial, 'Serial', Recording)
    SerialBridge('in-memory-only').close()
    SerialBridge('in-memory-only', baud=57600).close()
    assert opened == [module.DEFAULT_BAUD, 57600] and module.DEFAULT_BAUD == 115200

def test_trainer_output_handshake_is_rejected_without_opt_in(adapter):
    feed(adapter, f'READY 1 {adapter.session} PPM_YAW\n', 1)
    assert not adapter.ready and adapter.physical_output is False

@pytest.fixture
def trainer(monkeypatch):
    monkeypatch.setattr(module.serial, 'Serial', Serial)
    bridge = SerialBridge('in-memory-only', trainer_output=True)
    yield bridge
    bridge.close()

def test_opted_in_bridge_reports_trainer_output_from_ready(trainer):
    assert trainer.physical_output is False and 'PPM' not in trainer.transport
    feed(trainer, f'READY 1 {trainer.session} PPM_YAW\n', 1)
    assert trainer.ready and trainer.physical_output is True
    assert 'ESP32-S3' in trainer.transport and 'PPM' in trainer.transport
    assert SerialBridge.physical_output is False

def test_opted_in_bridge_without_jumper_is_ready_but_has_no_output(trainer):
    feed(trainer, f'READY 1 {trainer.session} NO_OUTPUT\n', 1)
    assert trainer.ready and trainer.physical_output is False and 'PPM' not in trainer.transport

def test_replayed_ready_cannot_change_the_session_output_mode(trainer):
    feed(trainer, f'READY 1 {trainer.session} NO_OUTPUT\n', 1)
    feed(trainer, f'READY 1 {trainer.session} PPM_YAW\n', 1.1)
    assert trainer.physical_output is False

def test_resync_drops_trainer_output_until_the_new_session_reports_it(trainer):
    feed(trainer, f'READY 1 {trainer.session} PPM_YAW\n', 1)
    old = trainer.session
    trainer.send(True, 200, 1.1)
    trainer.poll(1.1 + module.RESYNC_S)
    assert trainer.session != old and not trainer.ready and trainer.physical_output is False
    assert 'PPM' not in trainer.transport
    feed(trainer, f'READY 1 {old} PPM_YAW\n', 2.2)
    assert not trainer.ready
    feed(trainer, f'READY 1 {trainer.session} NO_OUTPUT\n', 2.3)
    assert trainer.ready and trainer.physical_output is False

@pytest.mark.parametrize('message', [
    b'\xff\xfe\n', b'unknown\n', b'x' * (MAX_FRAME + 1) + b'\n',
    'READY 1 other NO_OUTPUT\n', 'READY 1 {session} UNKNOWN\n',
    'HELLO 1 {session}\n', 'ACK 1 {session} 1 1 200 SEQUENCE\n',
    'ACK 1 {session} 9 1 200 NONE\n', 'ACK 1 {session} 1 1 201 NONE\n',
])
def test_bad_replies_do_not_refresh_ack(adapter, message):
    ready(adapter); adapter.send(True, 200, 1.1)
    before = adapter.last_ack
    if isinstance(message, str): message = message.format(session=adapter.session)
    assert feed(adapter, message, 1.15) == [] and adapter.last_ack == before and adapter.accepted_yaw == 0

def test_delayed_ack_is_rejected_and_old_outstanding_commands_expire(adapter):
    ready(adapter); adapter.send(True, 200, 1.1)
    assert feed(adapter, f'ACK 1 {adapter.session} 1 1 200 NONE\n', 1.35) == []
    adapter.send(True, 300, 2.2)
    assert list(adapter.outstanding) == [2]
    assert feed(adapter, f'ACK 1 {adapter.session} 2 1 300 NONE\n', 2.21) == [{'seq': 2, 'yaw': 300, 'fault': 'NONE'}]
    assert adapter.accepted_yaw == 300 and not adapter.outstanding

def test_oversized_unterminated_frame_discards_until_next_newline(adapter):
    ready(adapter); adapter.send(True, 200, 1.1)
    feed(adapter, b'x' * (MAX_FRAME + 1), 1.12)
    assert feed(adapter, f'ACK 1 {adapter.session} 1 1 200 NONE\n', 1.13) == []
    assert adapter.last_ack == 1 and adapter.accepted_yaw == 0
    assert feed(adapter, f'ACK 1 {adapter.session} 1 1 200 NONE\n', 1.14)

def test_partial_frames_preserve_data_and_multiple_replies_are_processed(adapter):
    message = f'READY 1 {adapter.session} NO_OUTPUT\n'
    assert feed(adapter, message[:8], 1) == [] and not adapter.ready
    feed(adapter, message[8:], 1.01); assert adapter.ready
    adapter.send(True, 250, 1.1); adapter.send(False, 0, 1.12)
    response = f'ACK 1 {adapter.session} 1 1 250 NONE\nACK 1 {adapter.session} 2 0 0 NONE\n'
    assert [r['yaw'] for r in feed(adapter, response, 1.13)] == [250, 0]
    assert adapter.accepted_yaw == 0

def test_close_releases_device_even_if_neutral_write_fails(adapter):
    ready(adapter)
    def broken(data): raise OSError('mock write error')
    adapter.serial.write = broken
    with pytest.raises(OSError): adapter.close()
    assert adapter.serial.closed
    adapter.ready = False

def test_invalid_mock_core_reply_never_enters_ack_queue(monkeypatch):
    bridge = MockBridge(); before = bridge.last_ack
    monkeypatch.setattr(bridge.core, 'receive', lambda *args: None)
    bridge.send(True, 200, 1)
    assert not bridge.pending and bridge.poll(1) == [] and bridge.last_ack == before


def test_oversized_discard_spans_chunks_and_keeps_next_valid_frame(adapter):
    ready(adapter); adapter.send(True, 200, 1.1)
    feed(adapter, b'x' * (MAX_FRAME + 1), 1.12)
    assert feed(adapter, b'not-a-delimiter', 1.13) == [] and not adapter.buffer
    response = f'ACK 1 {adapter.session} 1 1 200 NONE\n'
    assert feed(adapter, 'end-of-bad-frame\n' + response, 1.14)[0]['yaw'] == 200
    assert not adapter.discarding


def test_old_ack_cannot_undo_confirmed_neutral(adapter):
    ready(adapter); adapter.send(True, 500, 1.1); adapter.send(False, 0, 1.12)
    assert feed(adapter, f'ACK 1 {adapter.session} 2 0 0 NONE\n', 1.13)
    before = adapter.last_ack
    assert feed(adapter, f'ACK 1 {adapter.session} 1 1 500 NONE\n', 1.14) == []
    assert adapter.accepted_yaw == 0 and adapter.last_ack == before


def test_replayed_ready_does_not_hide_missing_command_ack(adapter):
    ready(adapter); adapter.send(True, 500, 1.1)
    assert feed(adapter, f'READY 1 {adapter.session} NO_OUTPUT\n', 1.3) == []
    assert adapter.last_ack == 1 and adapter.accepted_yaw == 0


@pytest.mark.parametrize('seed', range(8))
def test_random_wire_fragmentation_preserves_only_valid_ack(adapter, seed):
    import random
    rng = random.Random(seed)
    message = f'READY 1 {adapter.session} NO_OUTPUT\n'.encode()
    for byte in message: feed(adapter, bytes([byte]), 1)
    adapter.send(True, -600, 1.1)
    message = (b'bad\n\xff\n' + f'ACK 1 wrong 1 1 -600 NONE\nACK 1 {adapter.session} 1 1 -600 NONE\n'.encode())
    replies = []
    while message:
        size = rng.randint(1, 19); replies += feed(adapter, message[:size], 1.15); message = message[size:]
        assert len(adapter.buffer) <= 128
    assert replies == [{'seq': 1, 'yaw': -600, 'fault': 'NONE'}]
    assert adapter.accepted_yaw == -600 and adapter.last_ack == 1.15
