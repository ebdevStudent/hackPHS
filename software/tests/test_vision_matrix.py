"""Vision geometry/color matrices with independently constructed pixel fixtures."""
import itertools
import math

import cv2
import numpy as np
import pytest

from ball_demo.config import Settings
from ball_demo.vision import Detector
from ball_demo.sources import SCENARIOS, synthetic


@pytest.mark.parametrize('hue', range(180))
def test_every_opencv_hue_obeys_configured_range(hue):
    hsv = np.zeros((96, 128, 3), dtype=np.uint8)
    hsv[30:65, 40:75] = (hue, 255, 255)
    image = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    result = Detector().detect(image, Settings())
    if 35 <= hue <= 85:
        assert result and result['bbox'] == [40, 30, 35, 35]
        assert result['area'] == 34 * 34 and result['x'] == 57
        assert result['y'] == 47
    else: assert result is None


@pytest.mark.parametrize('width,height,x_fraction,radius', list(itertools.product(
    [160, 320, 640, 960], [240], [.1, .25, .5, .75, .9], [8, 12, 20, 30])))
def test_circle_position_scale_and_error_geometry(width, height, x_fraction, radius):
    x, y = max(radius+2,min(width-radius-3,round(width*x_fraction))), height//2
    image = np.zeros((height, width, 3), np.uint8)
    cv2.circle(image, (x,y), radius, (0,255,0), -1)
    result = Detector().detect(image, Settings(min_area=50))
    assert result and abs(result['x']-x) < 1 and abs(result['y']-y) < 1
    expected = (x-(width-1)/2)/((width-1)/2)
    assert result['error'] == pytest.approx(expected, abs=.003)
    assert -1 <= result['error'] <= 1 and 0 <= result['quality'] <= 1
    bx,by,bw,bh=result['bbox'];assert 0 <= bx < bx+bw <= width and 0 <= by < by+bh <= height
    assert result['area'] > 50 and result['area'] <= math.pi*radius*radius


@pytest.mark.parametrize('side', [5, 10, 15, 20, 30, 40])
@pytest.mark.parametrize('gate', ['below_min','on_min','on_max','above_max'])
def test_exact_rectangle_area_boundaries(side, gate):
    image=np.zeros((100,100,3),np.uint8);image[20:20+side,30:30+side]=(0,255,0)
    area=(side-1)**2
    limits={'below_min':(area+1,50000),'on_min':(area,50000),'on_max':(1,area),'above_max':(1,area-1)}
    lower,upper=limits[gate];d=Detector().detect(image,Settings(min_area=lower,max_area=upper))
    assert (d is not None) == (gate in ['on_min','on_max'])
    if d:assert d['area']==area


@pytest.mark.parametrize('scenario', SCENARIOS)
@pytest.mark.parametrize('index', [0, 1, 39, 40, 79, 80, 99, 100, 159, 160])
def test_every_synthetic_fixture_is_repeatable_and_truth_agrees(scenario,index):
    settings=Settings(width=320,height=240)
    first,truth=synthetic(index,settings,scenario);second,again=synthetic(index,settings,scenario)
    assert np.array_equal(first,second) and truth==again and first.shape==(240,320,3)
    assert type(truth['visible']) is bool
    if truth['clear']:
        d=Detector().detect(first,settings)
        assert (d is not None)==truth['visible']
        if d: assert abs(d['x']-truth['x'])<=5 and abs(d['y']-truth['y'])<=5


@pytest.mark.parametrize('misses', range(1,7))
@pytest.mark.parametrize('acquire', [1,2,3,5])
def test_detection_continuity_forgets_only_after_configured_misses(misses,acquire):
    settings=Settings(acquire_frames=acquire);d=Detector()
    image=np.zeros((240,320,3),np.uint8);cv2.circle(image,(100,100),15,(0,255,0),-1)
    assert d.detect(image,settings)['x']==100
    for _ in range(misses):assert d.detect(np.zeros_like(image),settings) is None
    assert (d.previous is None)==(misses>=acquire)
    cv2.circle(image,(250,100),25,(0,255,0),-1)
    found=d.detect(image,settings);assert found['x']==(250 if misses>=acquire else 100)
    assert d.misses==0
