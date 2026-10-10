"""Selected physical coupon mapping must survive final print orientations."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cage_model


def test_selected_coupon_bores_resolve_exactly():
    p=cage_model.parameters('p1b')
    assert p['rod_dia']+2*p['rod_bore_clear']==pytest.approx(1.275)
    assert p['m2_tap']==2.0
    assert p['bearing_od']+p['bearing_seat_clear']==pytest.approx(5.30)


@pytest.mark.parametrize('part,expected',[('inner_junction_X_pin',2.15),
    ('arm_pivot_block',2.25),('hub_pole_5way_pivot',2.25)])
def test_pin_diameter_follows_print_axis(part,expected):
    generator=cage_model.load_generator('build_p1b.py')
    p=cage_model.parameters('p1b')
    assert generator['pin_print_diameter'](p,part)==expected
    # The old shared field must never silently override these selected fits.
    p['pin_press_d']=1.0
    assert generator['pin_print_diameter'](p,part)==expected


def test_unknown_pin_part_cannot_silently_use_a_wrong_axis():
    generator=cage_model.load_generator('build_p1b.py')
    with pytest.raises(ValueError,match='Unknown pressed-pin'):
        generator['pin_print_diameter'](cage_model.parameters('p1b'),'new_adapter')


def test_final_running_gap_and_pin_stack_agree():
    p=cage_model.parameters('p1b')
    assert p['pivot_gap']==1.0
    assert p['pin_press_depth']+p['pivot_gap']+p['bearing_w']+1.5==11.0
