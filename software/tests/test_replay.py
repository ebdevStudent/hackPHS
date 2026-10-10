import csv
import json
import sys

from ball_demo import cli


def test_replay_preserves_sequence_and_never_opens_serial(tmp_path, monkeypatch):
    session = tmp_path / 'session'
    session.mkdir()
    rows = [{'t': '0', 'state': 'MANUAL', 'yaw': '0', 'x': '', 'y': '', 'error': '', 'quality': ''},
            {'t': '.15', 'state': 'LOCKED', 'yaw': '90', 'x': '500', 'y': '240', 'error': '.56', 'quality': '.94'},
            {'t': '.2', 'state': 'SEARCHING', 'yaw': '0', 'x': '', 'y': '', 'error': '', 'quality': ''}]
    with (session / 'samples.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader(); writer.writerows(rows)
    events = [{'t': 0, 'type': 'startup', 'data': {}}, {'t': .15, 'type': 'state', 'data': {'to': 'LOCKED'}},
              {'t': .2, 'type': 'state', 'data': {'to': 'SEARCHING'}}]
    (session / 'events.jsonl').write_text(''.join(json.dumps(e) + '\n' for e in events))
    def forbidden(*args, **kwargs): raise AssertionError('Replay opened a serial device')
    monkeypatch.setattr(cli, 'SerialBridge', forbidden)
    output = tmp_path / 'replay.json'
    monkeypatch.setattr(sys, 'argv', ['ball-demo', 'replay', str(session), '--output', str(output)])
    cli.main()
    result = json.loads(output.read_text())
    assert result['events'] == events
    assert [s['state'] for s in result['samples']] == ['MANUAL', 'LOCKED', 'SEARCHING']
    assert [s['yaw'] for s in result['samples']] == [0, 90, 0]
    # No config.json: the source kind is unknown and is labelled so rather than assumed synthetic.
    assert result['label'] == 'REPLAY / UNKNOWN session / no bridge output'
    assert result['video_included'] is False and result['session'] == 'session' and result['sources'] == []

