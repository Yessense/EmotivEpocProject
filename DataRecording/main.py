CHANNEL_NUM = 16

import sys
import os
import threading
from time import time

from PyQt5 import QtCore, QtGui, QtWidgets
from example_epoc_plus import EEG, tasks

cyHeadset = None

# При isDebugging = True программа не будет реагировать
#   на отсутствие гарнитуры
# Иначе, при нажатии на кнопку "Начать", если гарнитуру
#   не удалось найти, программа не будет отсчитывать время
isDebugging = False

try:
    cyHeadset = EEG()
except Exception as e:
    print(e)

imagesDir = 'images'
imagesFiles = os.listdir(imagesDir)

# Возможные классы - это все файлы в папке imagesDir без расширения:
types = [file[:file.rfind('.')] for file in imagesFiles]
data = []

imageSize = QtCore.QSize(640, 480)


class RecordingThread(threading.Thread):
    def __init__(self):
        super().__init__()

    def run(self):
        while (1):
            try:
                if w.isRecording():
                    # считывание данных с гарнитуры
                    while tasks.empty():
                        pass
                    data.append((time(), cyHeadset.get_data()))
            except Exception as e:
                print(e)


class Widget(QtWidgets.QWidget):
    _isRecording = False

    def __init__(self, types=['1', '2', '3']):
        global imagesDir
        super().__init__()
        self.types = types
        mainLayout = QtWidgets.QHBoxLayout()
        mainLayout.setAlignment(QtCore.Qt.AlignCenter)
        self.setLayout(mainLayout)

        self.radioButtons = [QtWidgets.QRadioButton(str(x)) for x in types]
        groupBox = QtWidgets.QGroupBox('Варианты')
        buttonsLayout = QtWidgets.QVBoxLayout()
        buttonsLayout.setAlignment(QtCore.Qt.AlignLeft)
        for b in self.radioButtons:
            buttonsLayout.addWidget(b)
        self.radioButtons[0].setChecked(True)
        groupBox.setLayout(buttonsLayout)

        menuLayout = QtWidgets.QVBoxLayout()
        menuLayout.setAlignment(QtCore.Qt.AlignTop)
        menuLayout.addWidget(groupBox)

        self.spinBox = QtWidgets.QSpinBox()
        self.spinBox.setMinimum(1)
        label = QtWidgets.QLabel("Время:")
        spinBoxLayout = QtWidgets.QHBoxLayout()
        spinBoxLayout.addWidget(label)
        spinBoxLayout.addWidget(self.spinBox)
        menuLayout.addLayout(spinBoxLayout)

        self.startButton = QtWidgets.QPushButton('Начать')
        self.stopButton = QtWidgets.QPushButton('Остановить')
        self.startButton.clicked.connect(self.startButtonClicked)
        self.stopButton.clicked.connect(self.stopButtonClicked)
        self.stopButton.clicked.connect(self.resetButton)

        menuLayout.addWidget(self.startButton)
        menuLayout.addWidget(self.stopButton)

        mainLayout.addLayout(menuLayout)

        self.imageWidget = QtWidgets.QLabel()
        self.imageWidget.setFixedSize(imageSize)
        mainLayout.addWidget(self.imageWidget)

    def isRecording(self):
        return self._isRecording

    def getType(self):
        for i in range(len(self.radioButtons)):
            if self.radioButtons[i].isChecked():
                return self.types[i]

    def startRecording(self):
        if self.isRecording():
            return
        self._isRecording = True
        print('start recording')
        self.countdown(self.spinBox.value())
        self.stopRecording()
        return

    def stopRecording(self):
        if not self.isRecording():
            return
        self._isRecording = False
        print('stop recording')
        self.resetButton()
        self.imageWidget.clear()
        self.optionWidget = QtWidgets.QWidget()
        self.optionWidget.setWindowTitle('Запись закончена')
        l = QtWidgets.QVBoxLayout()
        self.optionWidget.setLayout(l)
        l.addWidget(QtWidgets.QLabel('Сохранить данные?'))

        bl = QtWidgets.QHBoxLayout()
        bAccept = QtWidgets.QPushButton('Да')
        bAccept.clicked.connect(self.saveButtonClicked)
        bAccept.clicked.connect(self.optionWidget.close)
        bDecline = QtWidgets.QPushButton('Нет')
        bDecline.clicked.connect(self.eraseButtonClicked)
        bDecline.clicked.connect(self.optionWidget.close)
        bl.addWidget(bAccept)
        bl.addWidget(bDecline)
        l.addLayout(bl)
        self.optionWidget.setWindowModality(QtCore.Qt.ApplicationModal)
        self.optionWidget.setFixedSize(320, 120)
        self.optionWidget.show()

    def startButtonClicked(self):
        global cyHeadset
        if cyHeadset == None:
            try:
                cyHeadset = EEG()
            except Exception as e:
                print(e)
                if not isDebugging:
                    return
        self.setImageWidget(self.getType())
        self.countdown(3)
        self.startRecording()

    def countdown(self, seconds):
        self.startButton.setText(str(seconds))
        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.decreaseStartButtonTimer)
        loop = QtCore.QEventLoop()
        self.timeout.connect(loop.exit)

        timer.start(1000)
        loop.exec()
        timer.timeout.disconnect()
        timer.stop()

    timeout = QtCore.pyqtSignal()

    def decreaseStartButtonTimer(self):
        try:
            num = int(self.startButton.text())
            if num == 0:
                self.timeout.emit()
            else:
                self.startButton.setText(str(num - 1))

        except Exception as e:
            print(e)

    def resetButton(self):
        self.startButton.setText('Начать')
        self.startButton.setEnabled(True)

    def stopButtonClicked(self):
        self.stopRecording()

    def saveButtonClicked(self):
        global data
        file_name = "data.csv"

        # Открываем файл для записи измерений (append)
        f = open(file_name, 'a')

        # Если файл пустой - заполняем значения колонок
        if os.path.getsize(file_name) == 0:
            f.write('class,time,' + ','.join([str(i) for i in range(CHANNEL_NUM)]) + '\n')

        # Записываем данные
        for line in data:
            f.write(self.getType() + ',' + str(line[0]) + ',' + line[1] + '\n')

        f.close()

        # Очистка массива данных
        data = []

    def eraseButtonClicked(self):
        global data
        data = []

    def getImagesWidget(self, images):
        w = QtWidgets.QWidget()
        labels = [QtWidgets.QLabel() for x in range(len(images))]
        pixmaps = [QtGui.QPixmap(image) for image in images]
        for i in range(len(images)):
            labels[i].setPixmap(pixmaps[i])
        layout = None
        if len(images) <= 3:
            layout = QtWidgets.QHBoxLayout()
            for l in labels:
                layout.addWidget(l)
        else:
            layout = QtWidgets.QVBoxLayout()
            tempLayout = QtWidgets.QHBoxLayout()
            layout.addWidget(labels[0])
            for i in range(1, len(labels) - 1):
                tempLayout.addWidget(labels[i])
            tempLayout.setAlignment(QtCore.Qt.AlignCenter)
            layout.addLayout(tempLayout)
            layout.addWidget(labels[-1])
            layout.setAlignment(QtCore.Qt.AlignCenter)
            layout.setAlignment(labels[0], QtCore.Qt.AlignCenter)
            layout.setAlignment(labels[-1], QtCore.Qt.AlignCenter)
        w.setLayout(layout)
        return w

    def getImagePath(self, type):
        for image in imagesFiles:
            if type == image[:image.rfind('.')]:
                return imagesDir + '/' + image

    def setImageWidget(self, type):
        pixmap = QtGui.QPixmap(self.getImagePath(type))
        pixmap = pixmap.scaledToHeight(imageSize.height(), QtCore.Qt.SmoothTransformation)
        self.imageWidget.setPixmap(pixmap)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    w = Widget(types)
    w.show()
    recordingThread = RecordingThread()
    recordingThread.start()
    sys.exit(app.exec_())
