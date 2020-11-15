CHANNEL_NUM = 16


import sys
import os
import threading
from time import time

from PyQt5 import QtCore, QtGui, QtWidgets
from example_epoc_plus import EEG, tasks

cyHeadset = None

try:
    cyHeadset = EEG()
except Exception as e:
    print(e)

types = ['Вариант 1', 'Вариант 2', 'Вариант 3','Вариант 4','Вариант 5']
imagesDir = 'images'
data = []


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
            '''    
            # sleep будет необходимо убрать
            sleep(.5)
            '''


class Widget(QtWidgets.QWidget):
    _isRecording = False

    def __init__(self, types=['1', '2', '3']):
        global imagesDir
        super().__init__()
        self.types = types
        mainLayout = QtWidgets.QVBoxLayout()
        mainLayout.setAlignment(QtCore.Qt.AlignCenter)
        self.setLayout(mainLayout)

        self.radioButtons = [QtWidgets.QRadioButton(str(x)) for x in types]
        groupBox = QtWidgets.QGroupBox('Варианты')
        buttonsLayout = QtWidgets.QHBoxLayout()
        buttonsLayout.setAlignment(QtCore.Qt.AlignLeft)
        for b in self.radioButtons:
            buttonsLayout.addWidget(b)
        self.radioButtons[0].setChecked(True)
        groupBox.setLayout(buttonsLayout)
        mainLayout.addWidget(groupBox)

        menuLayout = QtWidgets.QHBoxLayout()
        self.startButton = QtWidgets.QPushButton('Начать')
        self.stopButton = QtWidgets.QPushButton('Остановить')
        self.startButton.clicked.connect(self.startButtonClicked)
        self.stopButton.clicked.connect(self.stopButtonClicked)
        self.stopButton.clicked.connect(self.resetButton)
        menuLayout.addWidget(self.startButton)
        menuLayout.addWidget(self.stopButton)

        self.spinBox = QtWidgets.QSpinBox()
        self.spinBox.setMinimum(1)
        label = QtWidgets.QLabel("Время:")
        menuLayout.addWidget(label)
        menuLayout.addWidget(self.spinBox)
        menuLayout.setAlignment(self.spinBox, QtCore.Qt.AlignRight)
        menuLayout.setAlignment(label, QtCore.Qt.AlignRight)
        mainLayout.addLayout(menuLayout)

        images = [('{}/{}'.format(imagesDir, x)) for x in os.listdir(imagesDir)]
        while (len(images) > len(types)):
            images.pop()

        mainLayout.addWidget(self.getImagesWidget(images))

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
        self.currentType = self.getType()
        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(True)
        time = self.spinBox.value() * 1000
        self.timer.start(time)
        self.timer.timeout.connect(self.stopRecording)

    def stopRecording(self):
        if not self.isRecording():
            return
        self._isRecording = False
        print('stop recording')
        self.timer.timeout.disconnect()
        self.resetButton()
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
                return
        self.startButton.setDisabled(True)
        timer = QtCore.QTimer(self)
        self.stopButton.clicked.connect(timer.stop)
        timer.setSingleShot(True)
        timer.timeout.connect(self.startRecording)
        timer.start(3000)

    def resetButton(self):
        self.startButton.setEnabled(True)

    def stopButtonClicked(self):
        self.stopRecording()

    def saveButtonClicked(self):
        global data
        file_name = self.currentType + ".csv"

        # Открываем файл для записи измерений
        f = open(file_name, 'a')

        # Если файл пустой - заполняем значения колонок
        if os.path.getsize(file_name) == 0:
            f.write('time,' + ','.join([str(i) for i in range(CHANNEL_NUM)]) + '\n')

        # Записываем данные
        for line in data:
            f.write(str(line[0]) + ',' + line[1] + '\n')

        f.close()

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


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    w = Widget(types)
    w.show()
    recordingThread = RecordingThread()
    recordingThread.start()
    sys.exit(app.exec_())
