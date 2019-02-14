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
from PyQt5.QtCore import Qt
import sys
from microscope import clients
import numpy as np

class MainWindow(QMainWindow):

    def __init__(self, parent=None):

        super(MainWindow, self).__init__(parent)
        self.form_widget = MainWidget(self)
        self.setCentralWidget(self.form_widget)
        self.resize(self.form_widget.width()+100, self.form_widget.height()+100)

    def closeEvent(self, event):
        self.show_flag = False
        QMainWindow.closeEvent(event)

class MainWidget(QWidget):

    def __init__(self, parent):
        super(MainWidget, self).__init__(parent)
        self.layout = QHBoxLayout(self)

        self.camera1 = CamInterfaceApp(self)
        self.layout.addWidget(self.camera1)

        self.camera2 = CamInterfaceApp(self)
        self.layout.addWidget(self.camera2)

        self.setLayout(self.layout)

        self.main_width = self.camera1.width() + self.camera2.width()
        self.main_height = max(self.camera1.height(), self.camera2.height())
        self.resize(self.main_width, self.main_height)


class CamInterfaceApp(QWidget):

    def __init__(self, parent):
        super(CamInterfaceApp, self).__init__(parent)
        self.layout = QVBoxLayout(self)

        self.camera = ImageApp()
        self.layout.addWidget(self.camera,85)

        self.buttons = ToggleButtonApp()
        self.layout.addWidget(self.buttons,15)

        self.setLayout(self.layout)

        self.app_width = min(self.camera.pixmap.width(),self.buttons.width())
        self.app_height = self.camera.pixmap.height() + 125
        self.resize(self.app_width,self.app_height)

class ToggleButtonApp(QWidget):

    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout(self)

        self.button1 = QPushButton("Live Image")
        self.layout.addWidget(self.button1)

        self.button2 = QPushButton("Alignment Centroid")
        self.layout.addWidget(self.button2)

        self.button3 = QPushButton("CurrentCentroid")
        self.layout.addWidget(self.button3)

        self.setLayout(self.layout)

        self.total_width = self.button1.width() + self.button2.width() + self.button3.width()
        self.total_height = self.button1.height()
        self.resize(self.total_width, self.total_height)

class ImageApp(QWidget):
 
    def __init__(self):
        super().__init__()
        self.title = 'PyQt5 image - pythonspot.com'
        self.left = 10
        self.top = 10
        self.width = 640
        self.height = 480
        self.initUI()
 
    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        
        # Create widget
        self.label = QLabel(self)

        qimage = QImage(np.zeros((512,512,3),dtype=np.uint8), 512, 512,
                        QImage.Format_RGB888)

        self.pixmap = QPixmap(qimage)
        self.label.setPixmap(self.pixmap)
        self.label.setAlignment(Qt.AlignHCenter)
        self.resize(self.pixmap.width(),self.pixmap.height())
        
        self.show()
 
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MainWindow()

    camera1 = clients.DataClient('PYRO:TestCamera@127.0.0.1:8000')
    camera1.enable()
    camera1.set_exposure_time(0.15)
    colimage1=np.zeros((512,512,3),dtype=np.uint8)

    camera2 = clients.DataClient('PYRO:TestCamera@127.0.0.1:8001')
    camera2.enable()
    camera2.set_exposure_time(0.15)
    colimage2 = np.zeros((512, 512, 3), dtype=np.uint8)

    ex.show_flag = True
    while(ex.show_flag):
        data1,timestamp1=camera1.trigger_and_wait()
        colimage1[:,:,0]=np.array(data1)
        colimage1[:,:,1]=colimage1[:,:,0]
        colimage1[:,:,2]=colimage1[:,:,0]
        qimage1 = QImage(colimage1, colimage1.shape[1], colimage1.shape[0],
                        QImage.Format_RGB888)

        data2, timestamp2 = camera2.trigger_and_wait()
        colimage2[:, :, 0] = np.array(data2)
        colimage2[:, :, 1] = colimage2[:, :, 0]
        colimage2[:, :, 2] = colimage2[:, :, 0]
        qimage2 = QImage(colimage2, colimage2.shape[1], colimage2.shape[0],
                         QImage.Format_RGB888)

        ex.form_widget.camera1.camera.pixmap = QPixmap(qimage1)
        ex.form_widget.camera2.camera.pixmap = QPixmap(qimage2)
        ex.form_widget.camera1.camera.label.setPixmap(ex.form_widget.camera1.camera.pixmap)
        ex.form_widget.camera2.camera.label.setPixmap(ex.form_widget.camera2.camera.pixmap)

        app.processEvents()
        ex.show()
    sys.exit(app.exec_())