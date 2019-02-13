from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QMainWindow, QPushButton
from PyQt5.QtGui import QPixmap, QImage
import sys
from microscope import clients
import numpy as np

class MainWindow(QMainWindow):

    def __init__(self, parent=None):

        super(MainWindow, self).__init__(parent)
        self.form_widget = MainWidget(self)
        self.setCentralWidget(self.form_widget)
        self.resize(self.form_widget.main_width+50, self.form_widget.main_height+50)

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

        self.main_width = self.camera1.app_width + self.camera2.app_width
        self.main_height = max(self.camera1.app_height, self.camera2.app_height)
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

        self.app_width = self.camera.pixmap.width()
        self.app_height = self.camera.pixmap.height() + 125
        self.resize(self.app_width,self.app_height)

class ToggleButtonApp(QWidget):

    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout(self)

        self.button1 = QPushButton("Button 1")
        self.layout.addWidget(self.button1)

        self.button2 = QPushButton("Button 2")
        self.layout.addWidget(self.button2)

        self.setLayout(self.layout)

        self.total_width = self.button1.width() + self.button2.width()
        self.total_height = self.button2.height()
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