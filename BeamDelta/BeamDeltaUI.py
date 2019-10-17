#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2019 Nicholas Hall <nicholas.hall@dtc.ox.ac.uk>
## 2019 David Miguel Susano Pinto <david.pinto@bioch.ox.ac.uk>
##
## This file is part of BeamDelta.
##
## BeamDelta is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## BeamDelta is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with BeamDelta.  If not, see <http://www.gnu.org/licenses/>.

import argparse
import sys

from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QLabel, QMainWindow,
                             QCheckBox, QPushButton, QShortcut, QVBoxLayout,
                             QWidget)

from PyQt5.QtGui import QImage, QKeySequence, QPainter, QPen

from PyQt5.QtCore import(QObject, QPoint, QSize, QTimer, Qt,
                         pyqtSignal, pyqtSlot)

import numpy as np
from skimage.filters import threshold_otsu
from scipy.ndimage.measurements import center_of_mass

import microscope.clients


class Imager(QObject):
    """Live acquisition imager.

    Starts acquiring images once enabled and sends an
    ``imageAcquired`` signal.

    Args:
        uri (str): URI for microscope device.
        exposure (float): time in seconds.
    """

    imageAcquired = pyqtSignal(np.ndarray)

    def __init__(self, uri, exposure):
        super().__init__()
        self._client = microscope.clients.DataClient(uri)
        self._client.set_exposure_time(exposure)

        self._image = np.zeros(self.shape(), dtype=np.uint8)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._acquire)

    def enable(self):
        self._client.enable()
        self._timer.start()

    def disable(self):
        self._timer.stop()
        self._client.disable()

    def shape(self):
        """Shape of images (width, height)"""
        return self._client.get_sensor_shape()

    def image(self):
        return self._image

    def _acquire(self):
        self._image = self._client.trigger_and_wait()[0]
        self.imageAcquired.emit(self._image)


class Alignment(QObject):
    """Model for an alignment.
    """
    changed = pyqtSignal()

    def __init__(self, imager):
        super().__init__()
        self._imager = imager
        self._image = self._imager.image()
        self._current = compute_beam_centre(self._image)
        self._reference = self._current

        self._imager.imageAcquired.connect(self.setCurrentImage)

    def reference(self):
        return self._reference

    def current(self):
        return self._current

    def image(self):
        return self._image

    @pyqtSlot(np.ndarray)
    def setCurrentImage(self, image):
        self._image = image
        self._current = compute_beam_centre(self._image)
        self.changed.emit()

    @pyqtSlot()
    def updateReference(self):
        self._reference = compute_beam_centre(self._imager.image())
        self.changed.emit()

    def offset(self):
        return tuple([c-r for c, r in zip(self._current, self._reference)])


def compute_beam_centre(image):
    """
    Returns:
        tuple with coordinates for centre ordered by dimension,
        i.e. (y, x)
    """
    try:
        thresh = threshold_otsu(image)
    except ValueError:
        ## Happens for example if all pixels in the image have the
        ## same value.  Return the middle of the image.
        return [l/2 for l in image.shape]

    masked = image.copy()
    masked[masked < thresh] = 0
    return [c for c in center_of_mass(masked)]


class MainWindow(QMainWindow):
    def __init__(self, imager1, imager2=None, parent=None):
        super().__init__(parent)
        self.setCentralWidget(CentralWidget(self, imager1, imager2))

        for sequence, slot in ((QKeySequence.FullScreen, self.toggleFullScreen),
                               (QKeySequence.Quit, self.close),
                               (QKeySequence.Close, self.close),):
            shortcut = QShortcut(sequence, self)
            shortcut.activated.connect(slot)

    @pyqtSlot()
    def toggleFullScreen(self):
        self.setWindowState(self.windowState() ^ Qt.WindowFullScreen)

class CentralWidget(QWidget):
    def __init__(self, parent, imager1, imager2=None):
        super().__init__(parent)
        self.camera1 = AlignmentControl(imager1)
        if imager2:
            self.camera2 = AlignmentControl(imager2)

        layout = QHBoxLayout(self)
        layout.addWidget(self.camera1)
        if imager2:
            layout.addWidget(self.camera2)
        self.setLayout(layout)


class AlignmentControl(QWidget):
    def __init__(self, imager):
        super().__init__()
        self._imager = imager
        self._alignment = Alignment(imager)
        self._visual = AlignmentVisual(self._alignment)
        self._text = AlignmentText(self._alignment)

        self._update_button = QPushButton('Update Reference')
        self._update_button.clicked.connect(self._alignment.updateReference)

        self._live_checkbox = QCheckBox("Live")
        self._live_checkbox.stateChanged.connect(self.changeLiveMode)

        self._live_checkbox.setChecked(True)

        layout = QVBoxLayout()
        layout.addWidget(self._visual, 1)

        buttons = QHBoxLayout()
        buttons.addWidget(self._update_button)
        buttons.addWidget(self._live_checkbox)
        layout.addLayout(buttons)

        layout.addWidget(self._text)
        self.setLayout(layout)

    @pyqtSlot(int)
    def changeLiveMode(self, state):
        if state == Qt.Checked:
            self._imager.enable()
        else:
            self._imager.disable()


class AlignmentText(QLabel):
    """Text "view" for Alignment"""
    def __init__(self, alignment):
        super().__init__()
        self.setAlignment(Qt.AlignHCenter)

        self._alignment = alignment
        self._alignment.changed.connect(self.updateText)

        self.updateText()

    @pyqtSlot()
    def updateText(self):
        self.setText("X distance = %f, Y distance = %f"
                     % self._alignment.offset())


class AlignmentVisual(QWidget):
    """Visual view for Alignment"""
    def __init__(self, alignment):
        super().__init__()
        self._alignment = alignment
        self._alignment.changed.connect(self.updateView)

    def sizeHint(self):
        return QSize(*self._alignment.image().shape)

    @pyqtSlot()
    def updateView(self):
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)

        image = self._alignment.image()
        painter.drawImage(self.rect(), QImage(image.tobytes(), *image.shape,
                                              QImage.Format_Grayscale8))

        painter.setCompositionMode(QPainter.CompositionMode_Lighten)
        pen = QPen()
        pen.setWidth(self.width()/500)
        pen.setCapStyle(Qt.RoundCap)

        painter.scale(self.width() / image.shape[0],
                      self.height() / image.shape[1])

        def drawCentre(color, x, y):
            pen.setColor(color)
            painter.setPen(pen)
            length = self.width() /50
            painter.translate(x, y)
            painter.drawLine(-length, -length, length, length)
            painter.drawLine(-length, length, length, -length)
            painter.drawEllipse(QPoint(0, 0), length/2, length/2)
            painter.translate(-x, -y)

        drawCentre(Qt.red, *self._alignment.reference())
        drawCentre(Qt.green, *self._alignment.current())


def parse_arguments(arguments):
    """Parse command line arguments.

    This is the list of arguments from :class:`QApplication`.  This is
    important so that Qt can filter out its own command line options.

    """
    parser = argparse.ArgumentParser(prog='BeamDelta')
    parser.add_argument('--exposure-time', dest='exposure_time',
                        action='store', type=float, default=0.15,
                        metavar='EXPOSURE-TIME',
                        help='exposure time for both cameras')
    parser.add_argument('cam1_uri', action='store', type=str,
                        metavar='CAM1-URI',nargs='+', help='URI for camera #1')
#    parser.add_argument('cam2_uri', action='store', type=str,
#                        default=None, required=False,
#                        metavar='CAM2-URI', help='URI for camera #2')
    return parser.parse_args(arguments[1:])


def __main__():
    """Construct BeamDelta UI.

    To run in the terminal, use::

        BeamDelta [exposure_time] [camera_1_uri] [camera_2_uri]"

    "exposure_time" has a default value of 150 ms. The camera URIs have the following format:

    "PYRO:[microscope_device_name]@[ip_address]:[port]"
    """
    if len(sys.argv) < 2:
        print("\nToo few parguments.\n", file=sys.stderr)
        print(__main__.__doc__, file=sys.stderr)
        sys.exit(1)
    elif len(sys.argv) > 5:
        print("\nToo many arguments.\n", file=sys.stderr)
        print(__main__.__doc__, file=sys.stderr)
        sys.exit(1)
    else:
        contructUI(sys.argv)



def contructUI(argv):
    app = QApplication(argv)
    app.setApplicationName('BeamDelta')
    app.setOrganizationName('Micron Oxford')
    app.setOrganizationDomain('micron.ox.ac.uk')

    args = parse_arguments(app.arguments())

    cam1 = Imager(args.cam1_uri[0], args.exposure_time)
    if len (args.cam1_uri)==2:
        cam2 = Imager(args.cam1_uri[1], args.exposure_time)
    else:
        cam2=None
        
    window = MainWindow(imager1=cam1, imager2=cam2)
    window.show()
    return app.exec()


if __name__ == '__main__':
    __main__()
