#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2019 Nicholas Hall <nicholas.hall@dtc.ox.ac.uk>
## Copyright (C) 2019 David Miguel Susano Pinto <david.pinto@bioch.ox.ac.uk>
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
                             QWidget,QInputDialog)

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
        self._exposure = exposure
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
    def __init__(self, imagers, parent=None):
        super().__init__(parent)
        self.setCentralWidget(CentralWidget(self, imagers))

        for sequence, slot in ((QKeySequence.FullScreen, self.toggleFullScreen),
                               (QKeySequence.Quit, self.close),
                               (QKeySequence.Close, self.close),):
            shortcut = QShortcut(sequence, self)
            shortcut.activated.connect(slot)

    @pyqtSlot()
    def toggleFullScreen(self):
        self.setWindowState(self.windowState() ^ Qt.WindowFullScreen)

class CentralWidget(QWidget):
    def __init__(self, parent, imagers):
        super().__init__(parent)
        self.cameras = [AlignmentControl(imager) for imager in imagers]

        layout = QHBoxLayout(self)
        for camera in self.cameras:
            layout.addWidget(camera)
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

        self._exposure_button = QPushButton('Change Exp')
        self._exposure_button.clicked.connect(self.changeExp)

        self._live_checkbox = QCheckBox("Live")
        self._live_checkbox.stateChanged.connect(self.changeLiveMode)

        self._live_checkbox.setChecked(True)

        layout = QVBoxLayout()
        layout.addWidget(self._visual, 1)

        buttons = QHBoxLayout()
        buttons.addWidget(self._update_button)
        buttons.addWidget(self._exposure_button)
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

    @pyqtSlot()
    def changeExp(self):
        exposure,ok = QInputDialog.getDouble(self,
                                             "Input dialog","Enter exposure (s)", self._imager._exposure, 0, 10, 3)
        liveState=self._live_checkbox.checkState
        if ok:
            self._imager._exposure = exposure
            if(liveState == Qt.Checked):
                self._imager.disable()
            self._imager._client.set_exposure_time(exposure)
            if(liveState == Qt.Checked):
                self._imager.enable()
        
class AlignmentText(QLabel):
    """Text "view" for Alignment"""
    def __init__(self, alignment):
        super().__init__()
        self.setAlignment(Qt.AlignHCenter)

        font = self.font()
        font.setPointSize(font.pointSize()*1.5)
        self.setFont(font)

        self._alignment = alignment
        self._alignment.changed.connect(self.updateText)

        self.updateText()

    @pyqtSlot()
    def updateText(self):
        self.setText("X distance = %.2f, Y distance = %.2f"
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

        def drawCentre(color, y, x):
            pen.setColor(color)
            painter.setPen(pen)
            length = self.width() /10
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
    parser.add_argument('cam_uris', action='store', type=str,
                        metavar='CAM-URI', nargs='+',
                        help='URIs for the cameras')
    return parser.parse_args(arguments[1:])


def main(argv):
    app = QApplication(argv)
    app.setApplicationName('BeamDelta')
    app.setOrganizationName('Micron Oxford')
    app.setOrganizationDomain('micron.ox.ac.uk')

    args = parse_arguments(app.arguments())

    cams = [Imager(uri, args.exposure_time) for uri in args.cam_uris]

    window = MainWindow(imagers=cams)
    window.show()
    return app.exec()


def __main__():
    # Entry point for setuptools.  The scripts created by setuptools
    # do not call the function with the command line arguments so a
    # separate function is needed for that.
    main(sys.argv)

if __name__ == '__main__':
    __main__()
