"""Per-motor flight trim via Betaflight custom mixer (tools/betaflight_motor_bench.py helpers)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import betaflight_motor_bench as bench  # noqa: E402


def test_all_full_weights_restore_stock_quadx():
    assert bench.trim_commands([1, 1, 1, 1]) == ['mixer QUADX', 'mmix reset']


def test_trim_keeps_betaflight_quadx_geometry_and_scales_throttle_only():
    cmds = bench.trim_commands([1, .95, 1, .95])
    assert cmds[:2] == ['mixer CUSTOM', 'mmix reset']
    assert cmds[2:] == ['mmix 0 1.000 -1.000 1.000 -1.000', 'mmix 1 0.950 -1.000 -1.000 1.000',
                        'mmix 2 1.000 1.000 1.000 1.000', 'mmix 3 0.950 1.000 -1.000 -1.000']


@pytest.mark.parametrize('bad', [[1, 1, 1], [1.1, 1, 1, 1], [.4, 1, 1, 1]])
def test_out_of_range_weights_rejected(bad):
    with pytest.raises(ValueError):
        bench.trim_commands(bad)


def test_parse_trim_from_cli_output():
    custom = ('mixer list\r\nAvailable: TRI QUADP QUADX BI GIMBAL CUSTOM\r\n# mixer\r\nMixer: CUSTOM\r\n# mmix\r\n'
              'mmix 0  1.000 -1.000  1.000 -1.000\r\nmmix 1  0.950 -1.000 -1.000  1.000\r\n'
              'mmix 2  1.000  1.000  1.000  1.000\r\nmmix 3  0.950  1.000 -1.000 -1.000\r\n')
    assert bench.parse_trim(custom) == {'mixer': 'CUSTOM', 'weights': [1.0, .95, 1.0, .95], 'custom_supported': True}
    stock = 'Available: QUADX\r\nMixer: QUADX\r\n'
    assert bench.parse_trim(stock) == {'mixer': 'QUADX', 'weights': [1.0] * 4, 'custom_supported': False}
