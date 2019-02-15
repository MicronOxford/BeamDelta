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
## along with BeamDeltaCOPYING.  If not, see <http://www.gnu.org/licenses/>.

from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, pyqtSlot
import sys
from microscope import clients
import numpy as np

class MainWindow(QMainWindow):

    def __init__(self, imager1, imager2, parent=None):

        super().__init__(parent)
        self.form_widget = MainWidget(self, imager1, imager2)
        self.setCentralWidget(self.form_widget)
        self.resize(self.form_widget.width()+100, self.form_widget.height()+100)
        self.show_flag = True

    def closeEvent(self, event):
        self.show_flag = False
        super().closeEvent(event)

class MainWidget(QWidget):

    def __init__(self, parent, imager1, imager2):
        super().__init__(parent)
        layout = QHBoxLayout(self)

        self.camera1 = CamInterfaceApp(self, imager1)
        self.camera2 = CamInterfaceApp(self, imager2)

        layout.addWidget(self.camera1)
        layout.addWidget(self.camera2)
        self.setLayout(layout)

        self.main_width = self.camera1.width() + self.camera2.width()
        self.main_height = max(self.camera1.height(), self.camera2.height())
        self.resize(self.main_width, self.main_height)


class CamInterfaceApp(QWidget):

    def __init__(self, parent, imager):
        super().__init__(parent)
        self.live_flag = True
        self.imager = None
        self.colimage = None
        self.setImager(imager)

        self.camera = ImageApp()
        self.buttons = ToggleButtonApp()
        self.buttons.live_button.clicked.connect(self.toggleLiveImage)

        layout = QVBoxLayout()
        layout.addWidget(self.camera)
        layout.addWidget(self.buttons)
        self.setLayout(layout)

        self.app_width = min(self.camera.pixmap.width(),self.buttons.width())
        self.app_height = self.camera.pixmap.height() + 125
        self.resize(self.app_width,self.app_height)

    def setImager(self,imager):
        self.imager = imager
        data, timestamp = self.imager.trigger_and_wait()
        data = np.array(data)
        self.colimage = np.zeros((data.shape[0], data.shape[1], 3), dtype=np.uint8)
        self.colimage[:, :, 0] = data
        self.colimage[:, :, 1] = self.colimage[:, :, 0]
        self.colimage[:, :, 2] = self.colimage[:, :, 0]

    def updateImage(self):
        if self.live_flag:
            data, timestamp = self.imager.trigger_and_wait()
            self.colimage[:, :, 0] = np.array(data)
            self.colimage[:, :, 1] = self.colimage[:, :, 0]
            self.colimage[:, :, 2] = self.colimage[:, :, 0]
            qimage = QImage(self.colimage, self.colimage.shape[1], self.colimage.shape[0],
                         QImage.Format_RGB888)

            self.camera.pixmap = QPixmap(qimage)
            self.camera.label.setPixmap(self.camera.pixmap)
        else:
            pass

    @pyqtSlot()
    def toggleLiveImage(self):
        self.live_flag = not(self.live_flag)

class ToggleButtonApp(QWidget):

    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)

        self.live_button = QPushButton("Live Image")

        self.align_cent_button = QPushButton("Alignment Centroid")
        self.curr_cent_button = QPushButton("CurrentCentroid")

        layout.addWidget(self.live_button)
        layout.addWidget(self.align_cent_button)
        layout.addWidget(self.curr_cent_button)
        self.setLayout(layout)

        self.total_width = self.live_button.width() + self.align_cent_button.width() \
                           + self.curr_cent_button.width()
        self.total_height = self.live_button.height()
        self.resize(self.total_width, self.total_height)

class ImageApp(QWidget):
    def __init__(self):
        super().__init__()
        self.label = QLabel(self)

        qimage = QImage(np.zeros((512,512,3),dtype=np.uint8), 512, 512,
                        QImage.Format_RGB888)
        self.pixmap = QPixmap(qimage)
        self.label.setPixmap(self.pixmap)

        layout = QHBoxLayout()
        layout.addWidget(self.label, 1, Qt.AlignHCenter)
        self.setLayout(layout)


if __name__ == '__main__':
    top_camera = clients.DataClient('PYRO:TestCamera@127.0.0.1:8000')
    top_camera.enable()
    top_camera.set_exposure_time(0.15)

    bottom_camera = clients.DataClient('PYRO:TestCamera@127.0.0.1:8001')
    bottom_camera.enable()
    bottom_camera.set_exposure_time(0.15)

    app = QApplication(sys.argv)
    ex = MainWindow(imager1=top_camera, imager2=bottom_camera)

    running = True
    while(running):
        ex.form_widget.camera1.updateImage()
        ex.form_widget.camera2.updateImage()

        app.processEvents()

        if ex.show_flag:
            ex.show()
        else:
            running = False