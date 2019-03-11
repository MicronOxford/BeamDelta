#!/usr/bin/env python
# -*- coding: utf-8 -*-

## Copyright (C) 2019 Nicholas Hall <nicholas.hall@dtc.ox.ac.uk>
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
                             QCheckBox, QVBoxLayout, QWidget)
from PyQt5.QtGui import QImage, QPainter, QPixmap
from PyQt5.QtCore import QObject, QSize, QTimer, Qt, pyqtSignal, pyqtSlot

from microscope import clients
import numpy as np
from skimage.filters import threshold_otsu
from scipy.ndimage.measurements import center_of_mass


class Imager(QObject):

    imageReceived = pyqtSignal(np.ndarray)

    def __init__(self, uri, exposure):
        super().__init__()
        self._client = clients.DataClient(uri)
        self._client.set_exposure_time(exposure)
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

    def _acquire(self):
        image = self._client.trigger_and_wait()[0]
        self.imageReceived.emit(image)


class MainWindow(QMainWindow):
    def __init__(self, imager1, imager2, parent=None):
        super().__init__(parent)
        self.form_widget = MainWidget(self, imager1, imager2)
        self.setCentralWidget(self.form_widget)


class MainWidget(QWidget):
    def __init__(self, parent, imager1, imager2):
        super().__init__(parent)
        self.camera1 = CamInterfaceApp(self, imager1)
        self.camera2 = CamInterfaceApp(self, imager2)

        layout = QHBoxLayout(self)
        layout.addWidget(self.camera1)
        layout.addWidget(self.camera2)
        self.setLayout(layout)


class CamInterfaceApp(QWidget):
    def __init__(self, parent, imager):
        super().__init__(parent)
        self.mid_x = None
        self.mid_y = None
        self.arm_length = None

        self.x_align_cent = None
        self.y_align_cent = None

        self.x_cur_cent = None
        self.y_cur_cent = None

        self.diff_x = None
        self.diff_y = None

        shape = imager.shape()
        self.colimage = np.zeros((shape[0], shape[1], 3), dtype=np.uint8)

        self.imager = imager
        self.imager.imageReceived.connect(self.updateView)

        self.view = CameraView(self.imager)

        self.live_button = QCheckBox("Live")
        self.live_button.stateChanged.connect(self.changeLiveMode)
        self.live_button.setChecked(True) # default to Live
        ## These are a bit misleading, because they don't control only
        ## show/hide, they may also reset a previous position.
        self.align_cent_button = QCheckBox("Show Reference")
        self.curr_cent_button = QCheckBox("Show Current")

        self.align_cent_button.stateChanged.connect(self.toggleAlignCent)
        self.curr_cent_button.stateChanged.connect(self.toggleCurrCent)
        self.text = QLabel(self)
        self.text.setAlignment(Qt.AlignHCenter)

        layout = QVBoxLayout()
        layout.addWidget(self.view, 1)

        buttons = QHBoxLayout()
        buttons.addWidget(self.live_button)
        buttons.addWidget(self.align_cent_button)
        buttons.addWidget(self.curr_cent_button)
        layout.addLayout(buttons)

        layout.addWidget(self.text)

        self.setLayout(layout)

    def updateView(self, image):
        if self.live_button.isChecked():
            #Collect live image
            self.colimage[:, :, 0] = np.array(image)
            self.colimage[:, :, 1] = self.colimage[:, :, 0]
            self.colimage[:, :, 2] = self.colimage[:, :, 0]

            self.updateAlignmentCentroid(self.colimage)
            self.updateCurrentCentroid(self.colimage)
            self.setCurrentImage(self.colimage)

            # Reset values overwritten by crosshairs
            self.colimage[:, :, 0] = np.array(image)
            self.colimage[:, :, 1] = self.colimage[:, :, 0]
            self.colimage[:, :, 2] = self.colimage[:, :, 0]
        else:
            # Copy last collected image as current frame
            paused_image = self.colimage.copy()
            self.updateAlignmentCentroid(paused_image)
            self.updateCurrentCentroid(paused_image)
            self.setCurrentImage(paused_image)

        if self.diff_y is None:
            self.text.setText("X distance = N/A, Y distance = N/A")
        else:
            self.text.setText("X distance = %f, Y distance = %f" % (self.diff_x, self.diff_y))

    def updateAlignmentCentroid(self, image):
        """Check if should be shown and update alignment centroid"""
        if not self.align_cent_button.isChecked():
            return

        if self.x_align_cent is None:
            ## Calculate position of alignment centroid if not yet done
            self.calcCurCentroid(image[:, :, 0])
            self.x_align_cent = self.x_cur_cent
            self.y_align_cent = self.y_cur_cent

        draw_crosshairs(image, self.x_align_cent, self.y_align_cent, 0)

    def updateCurrentCentroid(self, image):
        """Check if should be shown and update current centroid"""
        if not self.curr_cent_button.isChecked():
            return

        self.calcCurCentroid(image[:, :, 0])
        draw_crosshairs(image, self.x_cur_cent, self.y_cur_cent, 1)

    def setCurrentImage(self, image):
        """Set current image (with any crosshairs) as current frame"""
        self.view.updateImage(image)

    def calcCurCentroid(self, image):
        self.y_cur_cent, self.x_cur_cent = compute_beam_centre(image)
        if self.y_align_cent is None or self.x_align_cent is None:
            self.diff_x = None
            self.diff_y = None
        else:
            self.diff_y = self.y_cur_cent - self.y_align_cent
            self.diff_x = self.x_cur_cent - self.x_align_cent

    @pyqtSlot(int)
    def changeLiveMode(self, state):
        print(state)
        if state == Qt.Checked:
            print('enabel')
            self.imager.enable()
        else:
            self.imager.disable()

    @pyqtSlot(int)
    def toggleAlignCent(self, state):
        if state != Qt.Checked:
            self.x_align_cent = None
            self.y_align_cent = None
            self.diff_x = None
            self.diff_y = None

    @pyqtSlot(int)
    def toggleCurrCent(self, state):
        if state != Qt.Checked:
            self.diff_x = None
            self.diff_y = None


class CameraView(QWidget):
    def __init__(self, imager):
        super().__init__()
        self._imager = imager
        shape = self._imager.shape()
        self._image = None # FIXME: we should not have to deal with Nones
        self._setImage(np.zeros((self._shape[0], self._shape[1], 3),
                                dtype=np.uint8))

    def _setImage(self, image):
        ## XXX: I really don't like this
        self._image = QPixmap(QImage(image.tobytes(),
                                     image.shape[1], image.shape[0],
                                     QImage.Format_RGB888))

    def sizeHint(self):
        return QSize(*self._imager.shape())

    def updateImage(self, image):
        self._setImage(image)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self._image)


def compute_beam_centre(image):
    """
    Returns:
        tuple with coordinates for centre ordered by dimension,
        i.e. (y, x)
    """
    ## TODO: find out why we cut the 10px edges, and either comment
    ## here why it is done, or remove the removal of edges.
    edge_len = 10
    masked = image[edge_len:-edge_len, edge_len:-edge_len].copy()
    masked[masked < threshold_otsu(image)] = 0
    centre = center_of_mass(masked)
    centre = [c+edge_len for c in centre]
    return centre


def draw_crosshairs(image, x, y, channel):
    x = int(np.round(x))
    y = int(np.round(y))
    length = int(image.shape[1] * 0.05)

    val = np.iinfo(image.dtype).max
    image[y-length : y+length, x, channel] = val
    image[y, x-length : x+length, channel] = val


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
                        metavar='CAM1-URI', help='URI for camera #1')
    parser.add_argument('cam2_uri', action='store', type=str,
                        metavar='CAM2-URI', help='URI for camera #2')
    return parser.parse_args(arguments[1:])


def main(argv):
    app = QApplication(argv)
    app.setApplicationName('BeamDelta')
    app.setOrganizationName('Micron Oxford')
    app.setOrganizationDomain('micron.ox.ac.uk')

    args = parse_arguments(app.arguments())

    cam1 = Imager(args.cam1_uri, args.exposure_time)
    cam2 = Imager(args.cam2_uri, args.exposure_time)

    window = MainWindow(imager1=cam1, imager2=cam2)
    window.show()
    return app.exec()


if __name__ == '__main__':
    main(sys.argv)
