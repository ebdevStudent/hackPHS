"""Request shape, numeric type and atomicity contracts without capture threads."""
import copy
import itertools
import random

import pytest
from fastapi.testclient import TestClient
from ball_demo.api import create_app
from ball_demo.engine import Engine
from ball_demo.sources import Frame


@pytest.fixture
def api(tmp_path):
    engine=Engine(tmp_path)
    client=TestClient(create_app(engine,'matrix-token'))
    yield client,engine,{'Authorization':'Bearer matrix-token'}
    client.close();engine.stop()


NUMERIC_FIELDS=['gain','smoothing','deadband','max_yaw','slew_per_s','direction',
                'hue_low','hue_high','saturation_min','value_min','min_area','max_area']
@pytest.mark.parametrize('field,value',list(itertools.product(NUMERIC_FIELDS,
    [True,False,'1','0.5','NaN',[],{},'Infinity'])))
def test_settings_reject_coercible_and_invalid_types_atomically(api,field,value):
    client,e,auth=api;before=e.settings.dict();generation=e.generation
    reply=client.post('/api/operator/settings',json={field:value},headers=auth)
    assert reply.status_code==422 and e.settings.dict()==before and e.generation==generation
    assert not e.controller.enabled and e.controller.yaw==0


@pytest.mark.parametrize('value',[0,1,-1,2,'true','false','yes','no','1','0','on','off',None,[],{}])
def test_enable_requires_boolean_not_truthy_coercion(api,value):
    client,e,auth=api
    # Seed fresh source/bridge so accidental truthy coercion could enable.
    from ball_demo import engine as module
    now=module.time.monotonic();e.frame=Frame(None,now,1,{});e.bridge.last_ack=now
    reply=client.post('/api/operator/assist',json={'enabled':value},headers=auth)
    assert reply.status_code==422 and not e.controller.enabled and e.controller.yaw==0


@pytest.mark.parametrize('route,body',[
    ('assist',{'enabled':False}),('source',{'kind':'synthetic','scenario':'moving'}),
    ('settings',{'gain':10}),('fault',{'fault':'none'})])
@pytest.mark.parametrize('unknown',['enable','yaw','port','transport','gain_typo','__proto__'])
def test_unknown_operator_fields_are_rejected(api,route,body,unknown):
    client,e,auth=api;before=e.snapshot();reply=client.post('/api/operator/'+route,
        json={**body,unknown:123},headers=auth)
    assert reply.status_code==422
    after=e.snapshot();assert after['source']==before['source'] and after['settings']==before['settings']
    assert after['enabled']==before['enabled'] and after['yaw']==before['yaw']


@pytest.mark.parametrize('route',['assist','source','settings','fault'])
@pytest.mark.parametrize('body',['[]','null','42','"text"','{','{"x":'])
def test_non_object_and_truncated_requests_never_mutate(api,route,body):
    client,e,auth=api;before=e.settings.dict();generation=e.generation
    reply=client.post('/api/operator/'+route,content=body,headers={**auth,'Content-Type':'application/json'})
    assert reply.status_code==422 and e.settings.dict()==before and e.generation==generation


@pytest.mark.parametrize('seed',range(16))
def test_seeded_api_mutation_sequences_remain_neutral_and_atomic(api,seed):
    client,e,auth=api;rng=random.Random(5100+seed)
    for _ in range(30):
        route=rng.choice(['settings','source','reset','assist','fault'])
        good=rng.choice([True,False]);before=e.settings.dict();oldsource=copy.deepcopy(e.source_spec)
        if route=='settings':body={'gain':rng.randrange(2001) if good else -rng.randrange(1,2001)}
        elif route=='source':body={'kind':'synthetic','scenario':'centered' if good else 'missing'}
        elif route=='reset':body={};good=True
        elif route=='assist':body={'enabled':False if good else 'yes'}
        else:body={'fault':rng.choice(['none','disconnect','missing_ack','delayed_ack']) if good else 'unexpected'}
        reply=client.post('/api/operator/'+route,json=body,headers=auth)
        assert reply.status_code==(200 if good else 422)
        if not good:assert e.settings.dict()==before and e.source_spec==oldsource
        snapshot=client.get('/api/state').json()
        assert snapshot['enabled'] is False and snapshot['yaw']==0 and snapshot['physical_output'] is False
        assert snapshot['physical_telemetry'] is None
