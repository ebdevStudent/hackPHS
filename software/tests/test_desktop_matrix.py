"""Native client schema and request ordering matrices; no device/network access."""
import itertools
import json

import pytest
pytest.importorskip('PySide6')
from ball_demo import desktop
from test_desktop import client, state

pytestmark=pytest.mark.desktop

BAD_NUMBERS=[None,True,False,'1',[],{},float('nan'),float('inf'),-float('inf')]
@pytest.mark.parametrize('field,bad',list(itertools.product(['x','y','area','error','quality'],BAD_NUMBERS)))
def test_nested_detection_numeric_fields_never_accept_bad_types(field,bad):
    with pytest.raises(ValueError):desktop.validate_snapshot(state(detection={field:bad}))


@pytest.mark.parametrize('field,bad',list(itertools.product(['yaw','ack_yaw'],
    [None,True,False,'0',.5,[],{},-1001,1001])))
def test_command_measurements_require_bounded_wire_integers(field,bad):
    with pytest.raises(ValueError):desktop.validate_snapshot(state(**{field:bad}))


@pytest.mark.parametrize('field,bad',list(itertools.product(['frame_age_ms','ack_age_ms','processing_ms'],
    [True,False,'0',[],{},-.001,float('nan'),float('inf'),-float('inf')])))
def test_timing_fields_require_nonnegative_finite_measurements(field,bad):
    with pytest.raises(ValueError):desktop.validate_snapshot(state(**{field:bad}))


@pytest.mark.parametrize('field,bad',list(itertools.product(['source_label','session','bridge','bridge_fault'],
    [None,True,0,[],{}])))
def test_state_labels_must_be_text(field,bad):
    with pytest.raises(ValueError):desktop.validate_snapshot(state(**{field:bad}))


@pytest.mark.parametrize('required',list(state()))
def test_required_snapshot_fields_are_individually_enforced(required):
    # preview_index and physical_output are not currently rendered/required by
    # the snapshot schema. Test only its explicitly required measurements.
    value=state();del value[required]
    optional={'preview_index','physical_output'}
    if required in optional:desktop.validate_snapshot(value)
    else:
        with pytest.raises(ValueError):desktop.validate_snapshot(value)


@pytest.mark.parametrize('states',list(itertools.product([True,False],repeat=5)))
def test_all_five_assistance_queue_sequences_keep_neutral_priority(client,states):
    errors=[];client.failed.connect(errors.append)
    client.command('assist',{'enabled':True})
    queued=None;rejected=0
    for enable in states:
        client.command('assist',{'enabled':enable})
        if queued is False and enable:rejected+=1
        else:queued=enable
    assert len(client.network.calls)==1 and len(errors)==rejected
    first=client.network.calls[0][2];first.body=json.dumps(state(state='SEARCHING',enabled=True)).encode();first.finished.emit()
    assert len(client.network.calls)==2 and json.loads(client.network.calls[1][1])=={'enabled':queued}
    second=client.network.calls[1][2];second.body=json.dumps(state(state='SEARCHING' if queued else 'MANUAL',enabled=queued)).encode();second.finished.emit()
    assert not client.pending and not client.queued


@pytest.mark.parametrize('width,height,hz',list(itertools.product([1,160,640,1920],[1,120,480],[1,20,240])))
def test_trace_accepts_documented_dimension_rate_domain(width,height,hz):
    desktop.validate_trace({'settings':{'width':width,'height':height,'processing_hz':hz},
                           'samples':[{'t':0,'state':'MANUAL','yaw':0}]})


@pytest.mark.parametrize('state_name,enabled,yaw',list(itertools.product(
    ['MANUAL','SEARCHING','LOCKED','FAULT'],[True,False],[-650,0,650])))
def test_snapshot_state_enable_yaw_consistency(state_name,enabled,yaw):
    value=state(state=state_name,enabled=enabled,yaw=yaw)
    valid=(enabled==(state_name in ['SEARCHING','LOCKED'])) and (state_name=='LOCKED' or yaw==0)
    if valid:desktop.validate_snapshot(value)
    else:
        with pytest.raises(ValueError):desktop.validate_snapshot(value)
