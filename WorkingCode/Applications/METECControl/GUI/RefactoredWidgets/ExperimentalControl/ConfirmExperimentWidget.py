import logging

import PyQt5.QtCore as qtc
import PyQt5.QtGui as qtg
import PyQt5.QtWidgets as qtw
import pandas as pd
from Applications.METECControl.ExperimentDesigner.EventsTable import ComboBoxItemDelegate
from Applications.METECControl.GUI.ConfigSelectionWidget import Configs
from Applications.METECControl.GUI.RefactoredWidgets.BasicWidgets.DataFrameModel import DataFrameModel
from Framework.BaseClasses.Channels import ChannelType
from Framework.BaseClasses.Events import EventPayload, EventTypes
from Framework.BaseClasses.Package import Package
from PyQt5.QtPrintSupport import QPrintPreviewDialog


class ExperimentConfirmPopup:

    def __init__(self, GUIInterface):
        self.name = "ExperimentConfirmPopup"
        self.GUIInterface = GUIInterface
        self.popout = qtw.QDialog()
        self.layout = qtw.QGridLayout()
        self.popout.setLayout(self.layout)
        self.label_ep = qtw.QLabel(text="EP Config")
        self.label_fm = qtw.QLabel(text="FM Config")
        self.label_pressures = qtw.QLabel(text="FM Pressures")
        self.epConfigTable = EPConfigTable(GUIInterface)
        self.fmConfigTable = FMConfigTable(GUIInterface)
        self.pressuresTable = PressureConfigTable(GUIInterface)
        self.printButton = qtw.QPushButton(text="Print")
        self.printButton.clicked.connect(self.clicked_print)
        self.cancelButton = qtw.QPushButton(text="Cancel")
        self.cancelButton.clicked.connect(self.clicked_cancel)
        self.confirmButton = qtw.QPushButton(text="Confirm")
        self.confirmButton.clicked.connect(self.clicked_confirmButton)
        self.passAllButton = qtw.QPushButton(text="Pass All MVs")
        self.passAllButton.clicked.connect(self.clicked_passAll)
        self.check_CloseAfterSection = qtw.QCheckBox(text="Close After Section")
        self.check_CloseAfterIteration = qtw.QCheckBox(text="Close After Each Iteration")
        self.iterationsSpinbox = qtw.QSpinBox()
        self.iterationsSpinbox.setRange(1,999)

        self.printPreview = QPrintPreviewDialog()

        self.layout.addWidget(self.label_ep, 0, 1, 1, 3)
        self.layout.addWidget(self.epConfigTable, 1, 1, 1, 3)
        self.layout.addWidget(self.label_fm, 2, 1, 1, 3)
        self.layout.addWidget(self.fmConfigTable, 3, 1, 1, 3)
        self.layout.addWidget(self.label_pressures, 4, 1, 1, 3)
        self.layout.addWidget(self.pressuresTable, 5, 1, 1, 3)
        self.layout.addWidget(self.printButton, 6, 1, 1, 1)
        self.layout.addWidget(self.cancelButton, 6, 2, 1, 1)
        self.layout.addWidget(self.confirmButton, 6, 3, 1, 1)
        self.layout.addWidget(self.check_CloseAfterSection, 7, 1, 1, 1)
        self.layout.addWidget(self.check_CloseAfterIteration, 7, 2, 1, 1)
        self.layout.addWidget(self.passAllButton, 7, 3, 1, 1)
        self.layout.addWidget(qtw.QLabel(text="Iterations"), 8, 1)
        self.layout.addWidget(self.iterationsSpinbox, 8, 2)

    def clicked_passAll(self):
        self.epConfigTable.model().getDataFrame()['MV Verification'] = "Pass"
        self.fmConfigTable.model().getDataFrame()['MV Verification'] = "Pass"
        self.epConfigTable.clearVerificationBackground()
        self.fmConfigTable.clearVerificationBackground()
        self.epConfigTable.setFocus(qtc.Qt.MouseFocusReason)
        self.fmConfigTable.setFocus(qtc.Qt.MouseFocusReason)

    # slot
    def clicked_confirmButton(self, event):
        confirm = qtw.QMessageBox()
        confirm.setWindowTitle("Confirm Experiment")
        confirm.setStandardButtons(qtw.QMessageBox.Ok | qtw.QMessageBox.Cancel)
        if self.getErrorCount() > 0:
            confirm.setText("Confirm experiment with " + str(self.getErrorCount()) + " inconsistencies?")
        else:
            confirm.setText("Confirm experiment")
        ok = confirm.exec()
        if ok == qtw.QMessageBox.Ok:
            self.popout.accept()

    def getErrorCount(self):
        errors = 0
        errors += self.epConfigTable.getNumErrors()
        errors += self.fmConfigTable.getNumErrors()
        errors += self.pressuresTable.getNumErrors()
        return errors

    def clicked_print(self, event):
        printer = self.printPreview.printer()

        def paintRequested():
            painter = qtg.QPainter()
            painter.begin(printer)
            table = self.epConfigTable.grab()
            painter.drawText(30, 15, "EP Config")
            painter.drawPixmap(30, 40, table)
            table = self.fmConfigTable.grab()
            painter.drawText(30, 480, "FM config")
            painter.drawPixmap(30, 500, table)
            painter.end()

        self.printPreview.paintRequested.connect(paintRequested)
        self.printPreview.exec()

    # @staticmethod
    # def drawTable(painter, config, configName, y=0):
    #     font = painter.font()
    #     font.setBold(False)
    #     painter.setFont(font)
    #     painter.setPen(qtg.QPen(qtg.QColor(0, 0, 0)))
    #     painter.drawText(30, y, configName)
    #     lin = np.linspace(30, 500, len(config.columns))
    #     for i, v in enumerate(config.columns):
    #         painter.drawText(lin[i], y + 20, v)
    #     for i, row in config.df.iterrows():
    #         linI = 0
    #         for key, val in row.iteritems():
    #             if val == 'Fail':
    #                 font.setBold(True)
    #                 painter.setFont(font)
    #             else:
    #                 font.setBold(False)
    #                 painter.setFont(font)
    #             painter.drawText(lin[linI], i * 20 + y + 40, str(val))
    #             linI += 1

    def clicked_cancel(self, event):
        self.popout.reject()

    def getConfigs(self):
        fmConfigRecord = self.GUIInterface.getConfig(Configs.FMconfig)
        fmHeaders = ["Controller", "Flowmeter ID"]
        fmConfig = pd.DataFrame(columns=fmHeaders)
        if fmConfigRecord:
            fmConfig[fmHeaders] = fmConfigRecord['LoadedRecord'][fmHeaders]

        epConfigRecord = self.GUIInterface.getConfig(Configs.EPconfig)
        epHeaders = ["Emission Point", "Shorthand", "Active"]
        epConfig = pd.DataFrame(columns=epHeaders)
        if epConfigRecord:
            epConfig[epHeaders] = epConfigRecord['LoadedRecord'][epHeaders]

        # pressure columns=['Controller' 'Pressure (psia)']

    def buildFMTable(self, experimentFM, currentFM):
        fmHeaders = ["Controller", "Flowmeter ID"]
        df = pd.DataFrame(columns=self.fmConfigTable.columns)
        df['Controller'] = experimentFM.keys()
        df['Experiment'] = experimentFM.values() # Flowmeter ID column in experiment dataframe
        df['Current'] = None                     # Flowmeter ID column in current    dataframe
        df['MV Verification'] = "Fail"           # initially set all the manual valves to fail.
        numErrors = 0
        for i, row in df.iterrows():
            current = currentFM.loc[currentFM['Controller'] == row['Controller']]
            if len(current) == 0:
                raise KeyError(f'Missing Controller "{row["Controller"]}" in current FM Config')
            else:
                current = current.iloc[0]
            df.loc[i, 'Current'] = current['Flowmeter ID']   # set the current flowmeter to the ID in the current config.
            if df.loc[i, 'Experiment'] != df.loc[i, 'Current']:  # count and highlight errors
                numErrors += 1
                self.fmConfigTable.model().changeBackgroundColor(i, 1, qtg.QColor(255, 100, 100), True)
                self.fmConfigTable.model().changeBackgroundColor(i, 2, qtg.QColor(255, 100, 100), True)

        self.fmConfigTable.addData(df)
        for i in range(len(df)):
            self.fmConfigTable.highlightFails(i, self.fmConfigTable.columns.index('MV Verification'), 'Fail')
        self.fmConfigTable.resizeColumnsToContents()
        # self.errorCount += numErrors # uncommenting because it may be unnecessary? todo: check

    def buildPressuresTable(self, experimentPressures, currentPressures):
        df = pd.DataFrame(columns=self.pressuresTable.columns)
        df['Controller'] = experimentPressures.keys()
        df['Experiment (psia)'] = experimentPressures.values()
        df['Current (psia)'] = []
        numErrors = 0
        for i, row in df.iterrows():
            current = currentPressures.loc[currentPressures['Controller'] == row['Controller']]
            if len(current) == 0:
                raise KeyError(f'Missing Controller "{row["Controller"]}" in current pressures Config')
            else:
                current = current.iloc[0]
            df.loc[i, 'Current (psia)'] = current['Pressure (psia)']
            if df.loc[i, 'Experiment (psia)'] != df.loc[i, 'Current (psia)']:  # count and highlight errors
                numErrors += 1
                self.pressuresTable.model().changeBackgroundColor(i, 1, qtg.QColor(255, 100, 100), True)
                self.pressuresTable.model().changeBackgroundColor(i, 2, qtg.QColor(255, 100, 100), True)
        self.pressuresTable.addData(df)
        self.pressuresTable.resizeColumnsToContents()
        # self.errorCount += numErrors # uncommenting because it may be unnecessary? todo: check

    def initExperimentConfig(self, experimentConfig):
        self.epConfigTable.updateExperimentConfig(experimentConfig['Metadata']["EPConfig"])
        self.fmConfigTable.updateExperimentConfig(experimentConfig['Metadata']['FMConfig'])
        self.pressuresTable.updateExperimentConfig(experimentConfig['Metadata']['Pressures (psia)'])
        self.check_CloseAfterSection.setChecked(experimentConfig['Experiment']['CloseAfterSection'])
        self.check_CloseAfterIteration.setChecked(experimentConfig['Experiment']['CloseAfterIteration'])
        self.iterationsSpinbox.setValue(experimentConfig['Experiment']['Iterations'])

    def exec(self):
        self.popout.setGeometry(100, 100, 600, 800)
        isConfirmed = False
        if self.popout.exec():
            isConfirmed = True
        options = {
            "CloseAfterSection": self.check_CloseAfterSection.isChecked(),
            "CloseAfterIteration": self.check_CloseAfterIteration.isChecked(),
            "Iterations": int(self.iterationsSpinbox.value())
        }
        comparisons = {"Flow":{}, "EP":{}, "Pressures":{}}
        for rowName, row in self.fmConfigTable.model().getDataFrame().iterrows():
            comparisons['Flow'][rowName] = row.to_dict()
        for rowName, row in self.epConfigTable.model().getDataFrame().iterrows():
            comparisons['EP'][rowName] = row.to_dict()

        editEventPkg = Package(self.GUIInterface.getName(), channelType=ChannelType.Event, payload=EventPayload(self.GUIInterface.getName(), eventType=EventTypes.ExperimentEdit,
                                                               **options, comparisons=comparisons))  # emit event of edits made to experiment for logging purposes.
        self.GUIInterface.emitEvent(editEventPkg)
        return isConfirmed, options

class ConfigTable(qtw.QTableView):

    def __init__(self, GUIInterface, columns):
        self.numErrors = 0
        qtw.QTableView.__init__(self)
        self.GUIInterface = GUIInterface
        self.columns = columns
        self.df = pd.DataFrame(self.columns)
        model = DataFrameModel(self.df)
        self.setModel(model)

    def getNumErrors(self):
        return self.numErrors

    def highlightFails(self, row, col, val):
        i = self.model().getDataFrame().iloc[row].name
        if val == 'Fail':
            self.model().changeBackgroundColor(i, col, qtg.QColor(255, 100, 100))
        else:
            self.model().changeBackgroundColor(i, col, None)

    def clearVerificationBackground(self):
        col = self.columns.index("MV Verification")
        for i in self.model().getDataFrame().index:
            self.model().changeBackgroundColor(i, col, None)

class EPConfigTable(ConfigTable):
    def __init__(self, GUIInterface):
        columns = ["Outlet", "Experiment", "Current", "MV Active", "MV Verification",]
        ConfigTable.__init__(self, GUIInterface, columns)
        self.currentEP = None
        comboDelegate = ComboBoxItemDelegate(['Fail', 'Pass'])
        self.setItemDelegateForColumn(self.columns.index("MV Verification"), comboDelegate)
        model = DataFrameModel(self.df, 4)
        model.edited.connect(self.highlightFails)
        self.setModel(model)
        model.setEditableColumns([self.columns.index("MV Verification")])

    def updateExperimentConfig(self, outletMapping):
        self.df = pd.DataFrame(columns=self.columns)
        self.df["Outlet"] = outletMapping.values()
        self.df['Experiment'] = outletMapping.keys()
        self.df['MV Verification'] = ["Fail"]*len(outletMapping.keys())
        self.model().setDF(self.df)
        self.updateCurrentConfig()

    def updateCurrentConfig(self):
        try:
            epConfigRecord = self.GUIInterface.getSelectedSummary(Configs.EPconfig)
            self.currentEP = epConfigRecord
            for i, row in self.df.iterrows():
                try:
                    current = epConfigRecord.loc[epConfigRecord['Shorthand'] == row['Outlet']].iloc[0]
                    self.df.loc[i, "Current"] = current['Emission Point']
                    self.df.loc[i, "MV Active"] = "Pass" if current['Active'] == 1 else "Fail"
                except:
                    raise KeyError(f'Missing Shorthand "{row["Outlet"]}" in current EP Config')
            self.model().setDF(self.df)
            self.updateComparision()
        except Exception as e:
            logging.exception(f'Could not update current config comparison from experiment widget due to exception {e}')


    def updateComparision(self):
        self.numErrors = 0
        for i, row in self.df.iterrows():
            if self.df.loc[i, 'Experiment'] != self.df.loc[i, 'Current']:
                self.model().changeBackgroundColor(i, 1, qtg.QColor(255, 100, 100))
                self.model().changeBackgroundColor(i, 2, qtg.QColor(255, 100, 100))
                self.numErrors += 1
            if self.df.loc[i, 'MV Active'] == "Fail":
                self.numErrors += 1
            self.highlightFails(i, self.columns.index('MV Active'), self.df.loc[i, 'MV Active'])
            self.highlightFails(i, self.columns.index('MV Verification'), self.df.loc[i, 'MV Verification'])
        self.resizeColumnsToContents()
        self.model().setDF(self.df)


class FMConfigTable(ConfigTable):
    def __init__(self, GUIInterface):
        columns = ["Controller", "Experiment", "Current", "MV Verification"]
        ConfigTable.__init__(self, GUIInterface, columns)
        self.currentFM = None
        self.df = pd.DataFrame(columns=self.columns)
        comboDelegate = ComboBoxItemDelegate(['Fail', 'Pass'])
        self.setItemDelegateForColumn(len(self.columns) - 1, comboDelegate)
        model = DataFrameModel(self.df, 4)
        model.edited.connect(self.highlightFails)
        self.setModel(model)
        model.setEditableColumns([self.columns.index("MV Verification")])

    def updateExperimentConfig(self, experimentFM):
        fmHeaders = ["Controller", "Flowmeter ID"]
        df = pd.DataFrame(columns=self.columns)
        df['Controller'] = experimentFM.keys()
        df['Experiment'] = experimentFM.values()  # Flowmeter ID column in experiment dataframe
        df['Current'] = None  # Flowmeter ID column in current    dataframe
        df['MV Verification'] = "Fail"  # initially set all the manual valves to fail.
        self.df = df
        self.updateCurrentConfig()

    def updateCurrentConfig(self):
        try:
            fmrecord = self.GUIInterface.getSelectedSummary(Configs.FMconfig)
            self.currentFM = fmrecord
            for i, row in self.df.iterrows():
                current = fmrecord.loc[fmrecord['Controller'] == row['Controller']]
                if len(current) == 0:
                    raise KeyError(f'Missing Controller "{row["Controller"]}" in current FM Config')
                else:
                    current = current.iloc[0]
                self.df.loc[i, 'Current'] = current['Flowmeter ID']  # set the current flowmeter to the ID in the current config.
            self.model().setDF(self.df)
            self.resizeColumnsToContents()
            self.updateComparison()
        except Exception as e:
            logging.exception(f'Could not update current config comparison from experiment widget due to exception {e}')

    def updateComparison(self):
        self.numErrors = 0
        for i, row in self.df.iterrows():
            if self.df.loc[i, 'Experiment'] != self.df.loc[i, 'Current']:  # count and highlight errors
                    self.numErrors += 1
                    self.model().changeBackgroundColor(i, 1, qtg.QColor(255, 100, 100))
                    self.model().changeBackgroundColor(i, 2, qtg.QColor(255, 100, 100))
                    # self.model().changeBackgroundColor(i, 1, qtg.QColor(255, 100, 100), True)
                    # self.model().changeBackgroundColor(i, 2, qtg.QColor(255, 100, 100), True)
            # self.highlightFails(i, self.columns.index('MV Verification'), 'Fail')
            self.highlightFails(i, self.columns.index('MV Verification'), self.df.loc[i, 'MV Verification'])


class PressureConfigTable(ConfigTable):

    def __init__(self, GUIInterface):
        columns = ["Controller", "Experiment (psia)", "Current (psia)"]
        ConfigTable.__init__(self, GUIInterface, columns)
        self.currentFM = None
        self.df = pd.DataFrame(columns=self.columns)

    def updateExperimentConfig(self, experimentPressures):
        df = pd.DataFrame(columns=self.columns)
        df['Controller'] = experimentPressures.keys()
        df['Experiment (psia)'] = experimentPressures.values()
        df['Current (psia)'] = 0
        self.df = df
        self.updateCurrentConfig()

    def updateCurrentConfig(self):
        pressures =  None #get pressures from GUI
        if pressures:
            current = pressures
            self.currentPressures = current
            for i, row in self.df.iterrows():
                current = current.loc[current['Controller'] == row['Controller']]
                if len(current) == 0:
                    raise KeyError(f'Missing Controller "{row["Controller"]}" in current pressures Config')
                else:
                    current = current.iloc[0]
                self.df.loc[i, 'Current (psia)'] = current['Pressure (psia)']
            self.model().setDF(self.df)
            self.resizeColumnsToContents()
            self.updateComparison()
        else:
            pass

    def updateComparison(self):
        self.numErrors = 0
        for i, row in self.df.iterrows():
            if self.df.loc[i, 'Experiment (psia)'] != self.df.loc[i, 'Current (psia)']:  # count and highlight errors
                self.numErrors += 1
                self.model().changeBackgroundColor(i, 1, qtg.QColor(255, 100, 100), True)
                self.model().changeBackgroundColor(i, 2, qtg.QColor(255, 100, 100), True)