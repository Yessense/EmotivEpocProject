# constants
RECORDS_FILENAME = 'data.csv'
IMAGES_DIR = 'images'

# imports
import sys
import os
import threading
from time import time
from time import sleep

from PyQt5 import QtCore, QtGui, QtWidgets
from example_epoc_plus import EEG, tasks

# EEG class
cyHeadset = None

# При isDebugging = True программа не будет реагировать
#   на отсутствие гарнитуры
# Иначе, при нажатии на кнопку "Начать", если гарнитуру
#   не удалось найти, программа не будет отсчитывать время
isDebugging = False
'''
# Получаем сообщение об ошибке, если гарнитура не работает
try:
    cyHeadset = EEG()
except Exception as e:
    print(e)
'''
# Получаем список картинок
imagesFiles = os.listdir(IMAGES_DIR)

# Возможные классы - это все файлы в папке IMAGES_DIR без расширения:
types = [file[:file.rfind('.')] for file in imagesFiles]
data = []

# Размер, под высоту которого будут растягиваться изображения из IMAGES_DIR
imageSize = QtCore.QSize(640, 480)


class RecordingThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        while 1:
            try:
                if not self.running:
                    return
                if w.isRecording():
                    # считывание данных с гарнитуры
                    while tasks.empty():
                        if not self.running:
                            return
                    if cyHeadset is not None:
                        data.append((time(), cyHeadset.get_data()))
            except Exception as e:
                print(e)

    def stop(self):
        self.running = False


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

    def startRecording(self):
        if self.isRecording():
            return
        self._isRecording = True
        print('start recording')
        self.recordingThread = RecordingThread()
        self.recordingThread.start()
        self.countdown(self.spinBox.value())
        self.stopRecording()
        return

    def stopRecording(self):
        if not self.isRecording():
            return
        self._isRecording = False
        self.recordingThread.stop()
        # Отключение от гарнитуры
        global cyHeadset
        cyHeadset = None
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
        if cyHeadset is None:
            try:
                cyHeadset = EEG()
            except Exception as e:
                print(e)
                if not isDebugging:
                    return
        self.setImageWidget(self.getType())
        self.countdown(3)
        if self.countdownIsOk:
            self.startRecording()

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

    def stopButtonClicked(self):
        self.stopRecording()

    def saveButtonClicked(self):
        global data
        # Открываем файл для записи измерений (append)
        f = open(RECORDS_FILENAME, 'a')

        # Если файл пустой - заполняем значения колонок
        # Значения каналов "F3 FC5 AF3 F7 T7 P7 O1 O2 P8 T8 F8 AF4 FC6 F4"
        if os.path.getsize(RECORDS_FILENAME) == 0:
            f.write('class,time,' + ','.join("F3 FC5 AF3 F7 T7 P7 O1 O2 P8 T8 F8 AF4 FC6 F4".split(' ')) + '\n')

        # Записываем данные
        for line in data:
            f.write(self.getType() + ',' + str(line[0]) + ',' + line[1] + '\n')

        f.close()

        # Очистка массива данных
        data = []

        # Обносление счетчика
        self.countWidgets[self.getType()].increase()

    def eraseButtonClicked(self):
        global data
        data = []

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
        f = open(RECORDS_FILENAME)
        if os.path.getsize(RECORDS_FILENAME) != 0:  # if file has size
            f.readline()
            a = f.readline().split(',')

            count[a[0]] += 1
            lastTime = float(a[1])
            for line in f:
                a = line.split(',')
                if abs(float(a[1]) - lastTime) >= 3:
                    count[a[0]] += 1
                    lastTime = float(a[1])
            f.close()
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



    
def test1():
    # Проверка скорости считывания данных
    global tasks, cyHeadset
    if cyHeadset == None:
        try:
            cyHeadset = EEG()
        except Exception as e:
            print(e)
            return
    print('Текущий примерный размер tasks - ' + str(tasks.qsize()))
    sleep(1)
    print('Примерный размер tasks после 1 секунды считывания - '
          + str(tasks.qsize()))
    sleep(1)
    print('Примерный размер tasks после 2 секунд считывания - '
          + str(tasks.qsize()))
    sleep(1)
    print('Примерный размер tasks после 3 секунд считывания - '
          + str(tasks.qsize()))
    sleep(1)
    print('Примерный размер tasks после 4 секунд считывания - '
          + str(tasks.qsize()))
    sleep(1)
    print('Примерный размер tasks после 5 секунд считывания - '
          + str(tasks.qsize()))


def test2():
    # Проверка, как будет влиять на добавление данных
    #  в tasks удаление переменной cyHeadset
    global cyHeadset
    if cyHeadset == None:
        try:
            cyHeadset = EEG()
        except Exception as e:
            print(e)
            return
    print('Текущий примерный размер tasks: ' + str(tasks.qsize()))
    sleep(.5)
    cyHeadset = None
    print('Примерный размер tasks через 0,5 секунды работы cyHeadset: '
          + str(tasks.qsize()))
    print('cyHeadset удален')
    sleep(1)
    print('Примерный размер tasks через 1 секунду после удаления cyHeadset: '
          + str(tasks.qsize()))

def test3():
    # Проверка влияния на процессор постоянного
    #  считывания данных в data
    # Необходим test2
    global cyHeadset
    cyHeadset = None
    clearTasks()
    global cyHeadset
    try:
        cyHeadset = EEG()
    except Exception as e:
        print(e)
        return
    t = RecordingThread()
    print('Текущий примерный размер tasks - ' + str(tasks.qsize()))
    t.start()
    print('Считывание началось, ожидание 10 секунд')
    sleep(10)
    print('Текущий примерный размер tasks - ' + str(tasks.qsize()))
    

def test4():
    # Проверка объема времени на обработку
    #  данных из tasks
    # Допущение: возможно обработать данные из
    #  tasks через большой промежуток времени после
    #  их добавления
    # Требуется test1
    global tasks, cyHeadset
    if cyHeadset == None:
        try:
            cyHeadset = EEG()
        except Exception as e:
            print(e)
            return
    print('Считывание данных в течение 10 секунд...')
    sleep(1)
    print('Начало обработки 10*128 строк данных из tasks')
    t1 = time()
    for _ in range(10*128):
        cyHeadset.get_data()
    t2 = time()
    print('Для обработки потребовалось {} секунд'.format(t2 - t1))
    

    
    

if __name__ == '__main__':
    #test1()
    #test2()
    #test3()
    #test4()
    
    #app = QtWidgets.QApplication(sys.argv)
    #w = Widget(types)
    #w.show()
    
    #sys.exit(app.exec_())
