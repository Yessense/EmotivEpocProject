# constants
RECORDS_FILENAME = 'data.csv'
IMAGES_DIR = 'images'
ITER_COLUMN = 'iter'
CLASS_COLUMN = 'class'
SENSORS = 'F3 FC5 AF3 F7 T7 P7 O1 O2 P8 T8 F8 AF4 FC6 F4'.split(' ')
CSV_LABELS = [CLASS_COLUMN, ITER_COLUMN]
CSV_LABELS.extend(SENSORS)
# imports
import sys
import os
import threading
from time import time
from time import sleep
from random import choice

from PyQt5 import QtCore, QtGui, QtWidgets
from example_epoc_plus import EEG, tasks

# EEG class
cyHeadset = None

# При isDebugging = True программа предполагает, что подключение
#  гарнитуры не обязательно, и будет игнорировать ее отсутствие
isDebugging = False

# Получаем сообщение об ошибке, если гарнитура не работает
try:
    cyHeadset = EEG()
except Exception as e:
    print(e)

# Получаем список картинок
imagesFiles = os.listdir(IMAGES_DIR)

# Возможные классы - это все файлы в папке IMAGES_DIR без расширения:
types = [file[:file.rfind('.')] for file in imagesFiles]

# Размер, под высоту которого будут растягиваться изображения из IMAGES_DIR
imageSize = QtCore.QSize(640, 480)


class Widget(QtWidgets.QWidget):
    _isRecording = False

    def __init__(self, types=['1', '2', '3']):
        global IMAGES_DIR
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

    def setType(self, type):
        if self.types.count(type) == 0:
            return
        for i in range(len(self.radioButtons)):
            if self.radioButtons[i].text() == type:
                self.radioButtons[i].setChecked(True)
                return

    def startRecording(self):
        if self.isRecording():
            return
        self._isRecording = True
        print('start recording')
        
        sleep(.1) # Синхронизация с tasksCleaner
        
        # Очистка данных, которые были в считаны с гарнитуры до этого
        clearTasks()
        
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
        self.data = []
        # while not tasks.empty():
        if not isDebugging:
            if tasks.qsize() == 0:
                print('No data!!!')
            else:
                for _ in range(128 * self.spinBox.value()):
                    a = [self.getType(), str(self.get_iter_class_number())]
                    a.extend([str(value) for value in eval(cyHeadset.get_data())])
                    self.data.append(a)
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

                

    def countdown(self, seconds):
        self.startButton.setText(str(seconds))
        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.decreaseStartButtonTimer)
        loop = QtCore.QEventLoop()
        self.timeout.connect(loop.exit)
        self.countdownIsOk = True

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
            self.countdownIsOk = False
            self.timeout.emit()

    def resetButton(self):
        self.startButton.setText('Начать')
        self.startButton.setEnabled(True)
        self.randomStartButton.setEnabled(True)

    def stopButtonClicked(self):
        self.stopRecording()




    def saveButtonClicked(self):
        # Открываем файл для записи измерений (append)
        f = open(RECORDS_FILENAME, 'a')

        # Если файл пустой - заполняем значения колонок
        if os.path.getsize(RECORDS_FILENAME) == 0:
            f.write(','.join(CSV_LABELS) + '\n')

        # Записываем данные
        for line in self.data:
            f.write(','.join(line) + '\n')

        f.close()

        # Очистка массива данных
        self.data = []

        # Обносление счетчика
        self.countWidgets[self.getType()].increase()

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
        for image in imagesFiles:
            if type == image[:image.rfind('.')]:
                return IMAGES_DIR + '/' + image

    def setImageWidget(self, type):
        pixmap = QtGui.QPixmap(self.getImagePath(type))
        pixmap = pixmap.scaledToHeight(imageSize.height(), QtCore.Qt.SmoothTransformation)
        self.imageWidget.setPixmap(pixmap)

    def getTypesCount(self):
        # Получение количества сессий для каждого класса
        #   из файла с данными
        count = dict.fromkeys(self.types, 0)
        if not os.path.exists(RECORDS_FILENAME):
            f = open(RECORDS_FILENAME,'a')
            f.close()
    
        if os.path.getsize(RECORDS_FILENAME) != 0:  # if file has size
            try:
                f = open(RECORDS_FILENAME)
                labels = f.readline().split(',')
                a = f.readline().split(',')

                classCol = labels.index('class')
                iterCol = labels.index('iter')
                while self.types.count(a[classCol]) == 0 :
                    a = f.readline().split(',')
                count[a[classCol]] += 1
                lastIter = int(a[iterCol])
                lastClass = a[classCol]
                for line in f:
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
    if not w.isRecording():
        clearTasks()
    
def checkRecording():
    # Если за 0,2 секунды не считалось ничего, вывести ошибку
    count = tasks.qsize()
    if count != 0:
        return
    sleep(.1)
    count = tasks.qsize()
    if count != 0:
        return
    sleep(.1)
    count = tasks.qsize()
    if count != 0:
        return
    if not isDebugging:
        print('Данные не считываются!')

      
def recordingRestored():
    global isRecordingOk
    print('restored')
    isRecordingOk = True

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    w = Widget(types)
    w.show()

    # Очищает очередь tasks раз в секунду, если не идет запись
    tasksCleaner = QtCore.QTimer(w)
    tasksCleaner.timeout.connect(clearTasksIfNotRecording)
    tasksCleaner.start(1000)

    # Проверяет, считываются ли данные с гарнитуры
    recordingChecker = QtCore.QTimer(w)
    recordingChecker.timeout.connect(checkRecording)
    recordingChecker.start(500)
    
    sys.exit(app.exec_())
