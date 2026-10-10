"""Headless fake-display exercise of the flash stimulus, no Qt dependency or timing claim."""
import sys
from types import SimpleNamespace

from ball_demo.latency import QtFlash


def test_flash_stimulus_paints_black_then_centered_disc_and_closes(monkeypatch):
    paints=[]
    class App:
        @staticmethod
        def instance(): return None
        def __init__(self,args): self.calls=0
        def processEvents(self): self.calls+=1
    class Widget:
        def __init__(self): self.closed=False
        def rect(self): return (0,0,640,480)
        def width(self): return 640
        def height(self): return 480
        def setWindowTitle(self,text): self.title=text
        def showFullScreen(self): self.fullscreen=True
        def repaint(self): self.paintEvent(None)
        def close(self): self.closed=True
    class Painter:
        def __init__(self,widget): pass
        def fillRect(self,rect,color): paints.append(('background',rect,color))
        def setBrush(self,color): paints.append(('brush',color))
        def setPen(self,pen): paints.append(('pen',pen))
        def drawEllipse(self,*coords): paints.append(('ellipse',coords))
    monkeypatch.setitem(sys.modules,'PySide6.QtCore',SimpleNamespace(Qt=SimpleNamespace(PenStyle=SimpleNamespace(NoPen='no-pen'))))
    monkeypatch.setitem(sys.modules,'PySide6.QtGui',SimpleNamespace(QColor=lambda *args:args,QPainter=Painter))
    monkeypatch.setitem(sys.modules,'PySide6.QtWidgets',SimpleNamespace(QApplication=App,QWidget=Widget))
    flash=QtFlash()
    assert flash.window.fullscreen and flash.window.title=='Ball Drone latency target'
    flash(False)
    assert paints==[('background',(0,0,640,480),('black',))]
    flash(True)
    assert ('brush',(50,220,105)) in paints and ('ellipse',(176,96,288,288)) in paints
    flash.close()
    assert flash.window.closed and flash.app.calls==4
