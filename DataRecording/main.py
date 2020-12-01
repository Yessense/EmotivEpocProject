# constants
RECORDS_FILENAME = 'data.csv'
IMAGES_DIR = 'images'
ITER_COLUMN = 'iter'
CLASS_COLUMN = 'class'
SENSORS = 'F3 FC5 AF3 F7 T7 P7 O1 O2 P8 T8 F8 AF4 FC6 F4'.split(' ')
CSV_LABELS = [CLASS_COLUMN, ITER_COLUMN]
CSV_LABELS.extend(SENSORS)
DEFAULT_RECORDING_TIME = 5
HEADSET_FREQUENCY = 128
SECONDS_BETWEEN_PREDICTIONS = 0.25  # должно быть не больше 1.0
# imports
import sys
import os
from threading import Thread
from time import time
from time import sleep
from datetime import datetime
from random import choice
import numpy as np

from PyQt5 import QtCore, QtGui, QtWidgets
from example_epoc_plus import EEG, tasks

sys.path.insert(1, '../NN')

# EEG class
cyHeadset = None

# При isDebugging = True программа игнорирует отсутсвтие
# гарнитуры и не считывает с нее данные (даже если получилось
# подключиться)
isDebugging = os.path.exists('debugging')

# Получаем сообщение об ошибке, если гарнитура не работает
try:
    cyHeadset = EEG()
except Exception as e:
    print(e)

# Получаем список картинок
# imagesFiles = os.listdir(IMAGES_DIR)

# Возможные классы - это все файлы в папке IMAGES_DIR без расширения:
# types = [file[:file.rfind('.')] for file in imagesFiles]

# Размер, под высоту которого будут растягиваться изображения из IMAGES_DIR
imageSize = QtCore.QSize(640, 480)

# Размер индикатора, показывающего, удается ли получить
# данные с гарнитуры
recordingIndicatorSize = QtCore.QSize(20, 20)

data = []

mainWidget = None



class RecordingThread(Thread):
    def __init__(self, seconds, type, iterNumber):
        super().__init__()
        self.seconds = seconds
        self.type = type
        self.iterNumber = iterNumber
        self.data = []
        self._stopRecording = False

    def stopRecording(self):
        self._stopRecording = True

    def run(self):
        global cyHeadset
        if not isDebugging:
            for _ in range(self.seconds * HEADSET_FREQUENCY):
                if self._stopRecording:
                    break
                line = [self.type, str(self.iterNumber)]
                line.extend([str(value) for value
                             in eval(cyHeadset.get_data())])
                self.data.append(line)

    def getData(self):
        return self.data


class Widget(QtWidgets.QWidget):
    _isRecording = False
    timeout = QtCore.pyqtSignal()
    recordingInterrupted = QtCore.pyqtSignal()
    recordingOk = QtCore.pyqtSignal('bool')

    def __init__(self):
        global IMAGES_DIR
        super().__init__()
        self.setWindowTitle('Анализ ЭЭГ')
        self.recordingOk.connect(self.setRecordingOk)

        self.imagesDir = IMAGES_DIR + '/'

        self.recordingThread = None
        self.isRecordingOk = None

        self.imagesFiles = os.listdir(self.imagesDir)
        self.types = [file[:file.rfind('.')] for file in self.imagesFiles]

        mainLayout = QtWidgets.QHBoxLayout()
        mainLayout.setAlignment(QtCore.Qt.AlignCenter)
        self.setLayout(mainLayout)

        self.radioButtons = [QtWidgets.QRadioButton(str(x))
                             for x in self.types]
        groupBox = QtWidgets.QGroupBox('Варианты')

        buttonsLayout = QtWidgets.QVBoxLayout()
        buttonsLayout.setAlignment(QtCore.Qt.AlignLeft)
        for b in self.radioButtons:
            buttonsLayout.addWidget(b)
            b.clicked.connect(self.typeChanged)
        self.radioButtons[0].setChecked(True)
        groupBox.setLayout(buttonsLayout)

        menuLayout = QtWidgets.QVBoxLayout()
        menuLayout.setAlignment(QtCore.Qt.AlignTop)
        menuLayout.addWidget(groupBox)

        self.spinBox = QtWidgets.QSpinBox()
        self.spinBox.setMinimum(1)
        self.spinBox.setValue(DEFAULT_RECORDING_TIME)

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

        # Поле, в котором задается количество сессий при случайном выборе
        self.randomSessionCountInput = QtWidgets.QSpinBox()
        self.randomSessionCountInput.setValue(10)
        randomCountLabel = QtWidgets.QLabel('Случайные сессии:')
        randomCountInputLayout = QtWidgets.QHBoxLayout()
        randomCountInputLayout.addWidget(randomCountLabel)
        randomCountInputLayout.addWidget(self.randomSessionCountInput)
        randomCountInputLayout.setAlignment(self.randomSessionCountInput,
                                            QtCore.Qt.AlignRight)
        self.randomStartButton = QtWidgets.QPushButton('Случайный класс')
        self.randomStartButton.clicked.connect(self.randomStartButtonClicked)

        menuLayout.addLayout(randomCountInputLayout)
        menuLayout.addWidget(self.randomStartButton)

        count = self.getTypesCount()
        self.countWidgets = dict.fromkeys(self.types)
        for t in self.types:
            self.countWidgets[t] = CounterWidget(t, count[t], 0)
            menuLayout.addWidget(self.countWidgets[t])

        self.recordingIndicator = QtWidgets.QLabel()
        self.recordingIndicator.setFixedSize(recordingIndicatorSize)
        self.setRecordingOk(False)
        menuLayout.addWidget(self.recordingIndicator)

        menuLayout.setSpacing(7)
        mainLayout.addLayout(menuLayout)

        self.imageWidget = QtWidgets.QLabel()
        self.imageWidget.setFixedSize(imageSize)
        self.setImageWidget(self.getType())
        mainLayout.addWidget(self.imageWidget)

        mainLayout.setSpacing(40)

    def isRecording(self):
        return self._isRecording

    def getType(self):
        for i in range(len(self.radioButtons)):
            if self.radioButtons[i].isChecked():
                return self.types[i]

    def setType(self, type):
        if self.types.count(type) == 0:
            return
        for i in range(len(self.radioButtons)):
            if self.radioButtons[i].text() == type:
                self.radioButtons[i].setChecked(True)
                return

    def typeChanged(self, type):
        self.setImageWidget(self.getType())

    def startRecording(self):
        if self.isRecording():
            return
        self._isRecording = True
        # print('start recording')

        sleep(.1)  # Синхронизация с tasksCleaner

        # Очистка данных, которые были в считаны с гарнитуры до этого
        clearTasks()

        self.recordingThread = RecordingThread(self.spinBox.value(),
                                               self.getType(),
                                               self.get_iter_class_number())
        self.recordingInterrupted.connect(self.recordingThread.stopRecording)
        self.recordingThread.start()

        self.countdown(self.spinBox.value())
        self.stopRecording()

    def get_iter_class_number(self):
        return self.getItersCount(self.getType())

    def getItersCount(self, type):
        w = self.countWidgets[type]
        return w.getOldCount() + w.getNewCount()

    def stopRecording(self):
        if not self.isRecording():
            return

        self._isRecording = False
        # print('stop recording')

        # Удаление данных
        global data
        data = []

        self.resetButton()
        # self.imageWidget.clear()
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
        self.startButton.setDisabled(True)
        self.randomStartButton.setDisabled(True)
        global cyHeadset
        if cyHeadset is None:
            try:
                cyHeadset = EEG()
            except Exception as e:
                print(e)
                if not isDebugging:
                    self.resetButton()
                    return
        self.setImageWidget(self.getType())
        self.countdown(3)
        if self.countdownIsOk:
            self.startRecording()
        else:
            self.resetButton()

    def randomStartButtonClicked(self):
        counts = dict.fromkeys(self.types)
        for t in self.types:
            counts[t] = self.getItersCount(t)
        maxCount = self.randomSessionCountInput.value()
        allMax = True
        for t in self.types:
            if counts[t] < maxCount:
                allMax = False
                break
        if allMax:
            return
        t = choice(self.types)
        while counts[t] >= maxCount:
            t = choice(self.types)
        self.setType(t)
        self.startButtonClicked()

    def countdown(self, seconds, blocking=True):
        self.startButton.setText(str(seconds))
        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.decreaseStartButtonTimer)
        self.countdownIsOk = True
        timer.start(1000)
        if blocking:
            loop = QtCore.QEventLoop()
            self.timeout.connect(loop.exit)
            loop.exec()
        timer.timeout.disconnect()
        timer.stop()

    def decreaseStartButtonTimer(self):
        try:
            num = int(self.startButton.text())
            if num == 0:
                self.timeout.emit()
            else:
                self.startButton.setText(str(num - 1))

        except:
            self.countdownIsOk = False
            self.timeout.emit()

    def resetButton(self):
        self.startButton.setText('Начать')
        self.startButton.setEnabled(True)
        self.randomStartButton.setEnabled(True)

    def stopButtonClicked(self):
        self.recordingInterrupted.emit()
        self.stopRecording()

    def saveButtonClicked(self):
        try:
            data = self.recordingThread.getData()

            # Открываем файл для записи измерений (append)
            f = open(RECORDS_FILENAME, 'a')

            # Если файл пустой - заполняем значения колонок
            if os.path.getsize(RECORDS_FILENAME) == 0:
                f.write(','.join(CSV_LABELS) + '\n')

            # Записываем данные
            for line in data:
                l = [str(value) for value in line]
                f.write(','.join(l) + '\n')

            f.close()

            # Обносление счетчика
            self.countWidgets[self.getType()].increase()
        except Exception as e:
            print(e)

    def eraseButtonClicked(self):
        self.data = []

    def getImagesWidget(self, images):
        w = QtWidgets.QWidget()
        labels = [QtWidgets.QLabel() for _ in range(len(images))]
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
        for image in self.imagesFiles:
            if type == image[:image.rfind('.')]:
                return self.imagesDir + '/' + image

    def setImageWidget(self, type):
        pixmap = QtGui.QPixmap(self.getImagePath(type))
        pixmap = pixmap.scaledToHeight(imageSize.height(),
                                       QtCore.Qt.SmoothTransformation)
        self.imageWidget.setPixmap(pixmap)
        self.imageWidget.setFixedSize(pixmap.size())

    def getTypesCount(self):
        # Получение количества сессий для каждого класса
        #   из файла с данными
        count = dict.fromkeys(self.types, 0)
        if not os.path.exists(RECORDS_FILENAME):
            f = open(RECORDS_FILENAME, 'a')
            f.close()

        if os.path.getsize(RECORDS_FILENAME) != 0:  # if file has size
            try:
                f = open(RECORDS_FILENAME)
                labels = f.readline().split(',')
                a = f.readline().split(',')

                classCol = labels.index('class')
                iterCol = labels.index('iter')
                lines = f.read().split('\n')
                i = 0
                while self.types.count(a[classCol]) == 0:
                    a = lines[i].split(',')
                    i += 1
                    if i >= len(lines):  # Если в файле нет нужных типов
                        return count
                count[a[classCol]] += 1
                lastIter = int(a[iterCol])
                lastClass = a[classCol]
                for line in lines[i:]:
                    a = line.split(',')
                    if self.types.count(a[classCol]) == 0:
                        continue
                    if a[classCol] == lastClass:
                        if a[iterCol] != lastIter:
                            count[a[classCol]] += 1
                    else:
                        count[a[classCol]] += 1
                    lastClass = a[classCol]
                    lastIter = a[iterCol]
                f.close()
            except EOFError:
                pass
        return count

    def setRecordingOk(self, ok):
        if self.isRecordingOk == ok:
            return
        pixmap = QtGui.QPixmap(self.recordingIndicator.size())
        if ok:
            pixmap.fill(QtGui.QColor(0, 255, 0))
        else:
            pixmap.fill(QtGui.QColor(255, 0, 0))
        self.recordingIndicator.setPixmap(pixmap)
        self.isRecordingOk = ok


class CounterWidget(QtWidgets.QWidget):
    def __init__(self, type, oldCount, newCount=0):
        super().__init__()
        self.type = type
        self.oldCount = oldCount
        self.newCount = newCount

        self.typeLabel = QtWidgets.QLabel(self.type)
        self.countLabel = QtWidgets.QLabel(self.__getCountLabelText())
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.typeLabel)
        layout.addWidget(self.countLabel)
        layout.setAlignment(self.countLabel, QtCore.Qt.AlignRight)

        self.setLayout(layout)

    def __getCountLabelText(self):
        return '{} + {}'.format(self.oldCount, self.newCount)

    def __updateCount(self):
        self.countLabel.setText(self.__getCountLabelText())

    def setOldCount(self, count):
        self.oldCount = count
        self.__updateCount()

    def getOldCount(self):
        return self.oldCount

    def setNewCount(self, count):
        self.newCount = count
        self.__updateCount()

    def getNewCount(self):
        return self.newCount

    def increase(self):
        self.setNewCount(self.getNewCount() + 1)


def clearTasks():
    global tasks
    while not tasks.empty():
        tasks.get()


def clearTasksIfNotRecording():
    if not mainWidget.isRecording():
        clearTasks()


def checkRecording():
    # Если за 0,2 секунды не считалось ничего, вывести ошибку
    count = tasks.qsize()
    if count != 0:
        mainWidget.recordingOk.emit(True)
        return
    sleep(.1)
    count = tasks.qsize()
    if count != 0:
        mainWidget.recordingOk.emit(True)
        return
    sleep(.1)
    count = tasks.qsize()
    if count != 0:
        mainWidget.recordingOk.emit(True)
        return
    if not isDebugging and not mainWidget.isRecording():
        # print('Данные не считываются!')
        mainWidget.recordingOk.emit(False)
        global cyHeadset
        if cyHeadset is None:
            try:
                cyHeadset = EEG()
            except Exception as e:
                print(e)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    mainWidget = Widget()
    mainWidget.show()

    screenSize = app.desktop().size()
    mainWidget.move((screenSize.width() - mainWidget.width())//2,
                    (screenSize.height() - mainWidget.height())//2)

    # Очищает очередь tasks раз в секунду, если не идет запись
    tasksCleaner = QtCore.QTimer(mainWidget)
    tasksCleaner.timeout.connect(clearTasksIfNotRecording)
    tasksCleaner.start(1000)

    # Проверяет, считываются ли данные с гарнитуры
    recordingChecker = QtCore.QTimer(mainWidget)
    recordingChecker.timeout.connect(checkRecording)
    recordingChecker.start(500)

    sys.exit(app.exec_())
