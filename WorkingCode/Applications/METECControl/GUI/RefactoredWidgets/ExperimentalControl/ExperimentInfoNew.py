from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw

from Applications.METECControl.GUI.RefactoredWidgets.ExperimentalControl.CommonVariables import ROW_NAMES, COLUMN_NAMES
from Utils import QtUtils

FRAME_SIZE = (876, 190) # width and height
from Applications.METECControl.TestSuite.Deploying.DeployNew import TestScript

class ExpRunning(qtw.QFrame):

    def __init__(self, GUIInterface, name, parent, *args, **kwargs):
        qtw.QFrame.__init__(self, parent, *args)
        self.GUIInterface = GUIInterface
        self.name = name

        # not sure if specifying/saving the items is necessary, but doing it for potential memory management just in case.
        self.rowHeaderItems = {}
        self.colHeaderItems = {}

        # Will be double nested dictionary of source/GSH(row) -> descriptor(column) -> item.
        self.gshRowPointers = {}
        # self._addLayout()
        self.setupUi()
        self.linkGSHPointers()
        self.resetTable()
        # self._addActionWidget()

        # self.updateTimer = qtc.QTimer()
        # self.updateTimer.timeout.connect(self.checkTest)
        # self.updateTimer.start(100)

    def setupUi(self):
        self.resize(*FRAME_SIZE)
        self.setMinimumSize(qtc.QSize(*FRAME_SIZE))
        self.setMaximumSize(qtc.QSize(*FRAME_SIZE))
        self.setFrameShape(qtw.QFrame.Box)
        self.setFrameShadow(qtw.QFrame.Sunken)
        self.setLineWidth(2)
        self.setMidLineWidth(1)
        self.verticalLayout = qtw.QVBoxLayout(self)
        self.tableWidget = qtw.QTableWidget(self)
        self.tableWidget.setMinimumSize(qtc.QSize(0, 161))
        self.tableWidget.setMaximumSize(qtc.QSize(16777215, 161))
        self.tableWidget.setVerticalScrollBarPolicy(qtc.Qt.ScrollBarAlwaysOff)
        self.tableWidget.setHorizontalScrollBarPolicy(qtc.Qt.ScrollBarAlwaysOn)
        self.tableWidget.setSizeAdjustPolicy(qtw.QAbstractScrollArea.AdjustToContents)
        self.tableWidget.setDragEnabled(False)
        self.tableWidget.setAlternatingRowColors(True)
        # self.tableWidget.setObjectName("tableWidget")

        # setting up rows and their labels
        self.tableWidget.setRowCount(len(ROW_NAMES))
        for i in range(0, len(ROW_NAMES)):
            wi = qtw.QTableWidgetItem(ROW_NAMES[i])
            self.rowHeaderItems[ROW_NAMES[i]] = wi
            self.tableWidget.setVerticalHeaderItem(i, wi)

        # setting up columns and their labels.
        self.tableWidget.setColumnCount(len(COLUMN_NAMES))
        for j in range(0, len(COLUMN_NAMES)):
            wj = qtw.QTableWidgetItem(COLUMN_NAMES[j])
            self.colHeaderItems[COLUMN_NAMES[j]] = wj
            self.tableWidget.setHorizontalHeaderItem(j, wj)
        self.verticalLayout.addWidget(self.tableWidget)

    def linkGSHPointers(self):
        """ Fill the gshRowPointers nested dictionary with pointers to the tablewidgetitem at the gshName -> column name

        :return:
        """
        for rowNum in range(0, self.tableWidget.rowCount()):
            gshName = self.tableWidget.verticalHeaderItem(rowNum).text() # semi redundant due to that gshlabel being saved as an instance variable...
            self.gshRowPointers[gshName] = {}
            for colNum in range(0, self.tableWidget.columnCount()):
                colName = self.tableWidget.horizontalHeaderItem(colNum).text()
                item = qtw.QTableWidgetItem()
                self.tableWidget.setItem(rowNum, colNum, item)
                if colName == "Section_Progress":
                    pb = qtw.QProgressBar()
                    self.tableWidget.setCellWidget(rowNum, colNum, pb)
                else:
                    tw = qtw.QLabel("---")
                    self.tableWidget.setCellWidget(rowNum, colNum, tw)
                self.gshRowPointers[gshName][colName] = item

    def resetTable(self):
        for sourceName in ROW_NAMES:
            self.resetRow(sourceName)

    def getTableWidget(self, sourceName, colName):
        item = self.gshRowPointers[sourceName][colName]
        row = self.tableWidget.row(item)
        col = self.tableWidget.column(item)
        w = self.tableWidget.cellWidget(row, col)
        return w

    def resetRow(self, sourceName):
        for colName in COLUMN_NAMES:
            w = self.getTableWidget(sourceName, colName)
            if colName == "Section_Progress":
                w.reset()
            else:
                w.setText('---')

if __name__ == '__main__':
    app = QtUtils.getApp()
    w = ExpRunning(None, "ExperimentRunning", None)
    # with open("C:\\Users\\CSU\\Documents\\SVN_METEC\\Operations\\AutomatedExperiments\\2021 Continuous Monitoring Pad 45\\Config 2 - 75 SLPM\\MV Left\\30min_1CR_4S-23_14slpm.json") as j:
    #     scriptDict = json.load(j)
    # script = TestScript(None, scriptDict)
    # w.acceptTest(script)
    w.show()
    s = QtUtils.StartApp()
    s.start()