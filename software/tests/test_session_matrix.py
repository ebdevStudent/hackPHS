"""CSV/JSONL evidence round trips with independent percentile/count calculations."""
import csv
import json
import random

import pytest
from ball_demo.config import Settings
from ball_demo.session import Session


@pytest.mark.parametrize('seed',range(50))
def test_logged_sessions_roundtrip_counts_measurements_and_events(tmp_path,seed,monkeypatch):
    from ball_demo import session as module
    now=[100.];monkeypatch.setattr(module.time,'monotonic',lambda:now[0])
    rng=random.Random(88000+seed);settings=Settings(gain=rng.randint(0,2000));source={'kind':'synthetic','scenario':'moving'}
    s=Session(tmp_path,settings,source);samples=[];timings=[];faults=0
    count=rng.randint(0,70)
    for index in range(count):
        now[0]+=.05;fault=index%7==0
        if fault:faults+=1;s.event('fault',{'reason':'quoted "reason", newline\nµ','yaw':0})
        processing=None if index%4==0 else round(rng.uniform(0,50),3)
        value={'state':'FAULT' if fault else 'MANUAL','enabled':False,'yaw':0,'ack_yaw':0,
            'detection':None if index%3==0 else {'x':index+.25,'y':index+.75,'error':-.2,'quality':.8},
            'frame_age_ms':index*.5,'ack_age_ms':index*.25,'processing_ms':processing}
        s.sample(value);samples.append(value)
        if processing is not None:timings.append(processing)
    now[0]+=.05;s.event('shutdown',{'yaw':0});s.close(count*2)
    summary=json.loads((s.path/'summary.json').read_text());config=json.loads((s.path/'config.json').read_text())
    rows=list(csv.DictReader((s.path/'samples.csv').open()));events=[json.loads(v) for v in (s.path/'events.jsonl').read_text().splitlines()]
    assert summary['control_samples']==count==len(rows) and summary['faults']==faults
    assert summary['frames']==count*2 and summary['duration_s']==pytest.approx((count+1)*.05)
    assert summary['processing_fps']==pytest.approx(count*2/summary['duration_s'])
    expected=sorted(timings)[int(.95*(len(timings)-1))] if timings else None
    assert summary['processing_ms_p95']==expected and summary['physical_output'] is False
    assert summary['physical_measurements'] is None and config['settings']==settings.dict() and config['source']==source
    assert events[-1]['type']=='shutdown' and all(e['data']['yaw']==0 for e in events)
    assert sum(e['type']=='fault' for e in events)==faults
    assert all(a['t']<=b['t'] for a,b in zip(events,events[1:]))
    for row,value in zip(rows,samples):
        assert row['state']==value['state'] and row['enabled']=='False' and int(row['yaw'])==0
        if value['detection']:assert float(row['x'])==value['detection']['x'] and float(row['quality'])==.8
        else:assert row['x']==row['y']==row['error']==row['quality']==''
        assert row['processing_ms']==('' if value['processing_ms'] is None else str(value['processing_ms']))
    assert s.events.closed and s.samples.closed
