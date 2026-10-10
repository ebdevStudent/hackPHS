"""Controller reference trajectories across gains, smoothing, sign and timing."""
import itertools
import random

import pytest

from ball_demo.config import Settings
from ball_demo.control import Controller


@pytest.mark.parametrize('gain,smoothing,direction,acquire,dt', list(itertools.product(
    [0,100,700,2000], [.1,.35,1], [-1,1], [1,3], [0,.001,.05,.4])))
def test_controller_matches_independent_discrete_reference(gain,smoothing,direction,acquire,dt):
    settings=Settings(gain=gain,smoothing=smoothing,direction=direction,acquire_frames=acquire)
    c=Controller();c.enable(True);filtered=0.;output=0
    errors=[-1,-.6,-.04,0,.04,.3,1]*7
    for index,error in enumerate(errors):
        actual=c.frame({'error':error},settings,dt)
        if index+1 < acquire:assert actual==0 and c.state=='SEARCHING';continue
        filtered=(1-smoothing)*filtered+smoothing*error
        wanted=direction*gain*(0 if abs(filtered)<=settings.deadband else filtered)
        wanted=max(-settings.max_yaw,min(settings.max_yaw,wanted))
        allowance=settings.slew_per_s*min(max(dt,0),.1)
        expected=round(min(max(wanted,output-allowance),output+allowance))
        assert actual==expected and c.filtered==pytest.approx(filtered,abs=1e-12)
        assert abs(actual-output)<=allowance+.500000001
        assert abs(actual)<=settings.max_yaw and c.state=='LOCKED'
        output=expected
    c.frame(None,settings,dt)
    assert c.yaw==c.filtered==c.count==0 and c.state=='SEARCHING'


@pytest.mark.parametrize('seed',range(80))
def test_seeded_state_machine_recovers_only_after_operator_enable(seed):
    rng=random.Random(104000+seed);c=Controller();s=Settings(acquire_frames=rng.randint(1,6),
        max_yaw=rng.randint(0,1000),gain=rng.uniform(0,2000),smoothing=rng.uniform(.01,1),
        slew_per_s=rng.uniform(.1,10000),direction=rng.choice([-1,1]))
    enabled=False;count=0;expected='MANUAL'
    for _ in range(150):
        action=rng.choice(['enable','disable','fault','loss','frame','frame','frame'])
        if action in ['enable','disable']:
            enabled=action=='enable';count=0;expected='SEARCHING' if enabled else 'MANUAL';c.enable(enabled)
        elif action=='fault':enabled=False;count=0;expected='FAULT';c.fail('injected')
        else:
            detection=None if action=='loss' else {'error':rng.uniform(-1,1)}
            c.frame(detection,s,rng.uniform(-.1,.5))
            if not enabled:count=0
            elif detection is None:count=0;expected='SEARCHING'
            else:
                count+=1
                if count>=s.acquire_frames:expected='LOCKED'
        assert c.enabled==enabled and c.state==expected and c.count==count
        assert type(c.yaw) is int and abs(c.yaw)<=s.max_yaw
        if expected!='LOCKED':assert c.yaw==0
        if expected=='FAULT':assert c.fault=='injected'
        else:assert c.fault is None
    assert all(e['from']!=e['to'] for e in c.events)
