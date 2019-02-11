from PyQt5.QtWidgets import QApplication, QWidget, QLabel
from PyQt5.QtGui import QIcon, QPixmap,QImage
import sys
from microscope import clients
import time
import numpy as np

class App(QWidget):
 
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
    ex = App()

    camera = clients.DataClient('PYRO:TestCamera@127.0.0.1:8000')
    camera.enable()
    camera.set_exposure_time(0.15)
    colimage=np.zeros((512,512,3),dtype=np.uint8)

    while(1):
        data,timestamp=camera.trigger_and_wait()
        colimage[:,:,0]=np.array(data)
        colimage[:,:,1]=colimage[:,:,0]
        colimage[:,:,2]=colimage[:,:,0]
        qimage = QImage(colimage, colimage.shape[1], colimage.shape[0],
                        QImage.Format_RGB888)

        ex.pixmap = QPixmap(qimage)
        ex.label.setPixmap(ex.pixmap)
        ex.show()

    sys.exit(app.exec_())

