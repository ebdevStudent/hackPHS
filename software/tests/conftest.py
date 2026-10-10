"""Qt is optional for core tests; desktop verification requires it explicitly."""
import os
import shutil
import sys
import tempfile

import pytest


@pytest.fixture(scope='session')
def qapp():
    pytest.importorskip('PySide6')
    from PySide6.QtCore import QLibraryInfo, QFileInfo, QCoreApplication
    from PySide6.QtWidgets import QApplication
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    cache = None
    plugins = QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)
    if sys.platform == 'darwin' and QFileInfo(plugins + '/platforms/libqoffscreen.dylib').isHidden():
        cache = tempfile.TemporaryDirectory(prefix='ball-test-qt-', dir='/tmp')
        shutil.copytree(plugins, cache.name, dirs_exist_ok=True, copy_function=shutil.copy)
        os.environ['QT_PLUGIN_PATH'] = cache.name
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = cache.name + '/platforms'
        QCoreApplication.setLibraryPaths([cache.name])
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    yield app
    app.processEvents()
    if cache: cache.cleanup()


def pytest_configure(config):
    config.addinivalue_line('markers', 'desktop: requires optional Qt desktop dependencies')
    config.addinivalue_line('markers', 'process: uses a real local server subprocess')
