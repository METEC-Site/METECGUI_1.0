import csv
import json
import os
import pathlib
import sys

from PyQt5 import QtCore as qtc, QtWidgets as qtw

from Applications.METECControl.GUI.RefactoredWidgets.BasicWidgets.DataFrameModel import DataFrameModel

sys.path.insert(0, os.getcwd())

import PyQt5.QtCore as qtc
import PyQt5.QtWidgets as qtw
import pandas as pd  # NOTE: pandas writing and reading excel also needs packages 'xlrs' and 'openpyxl'
from Applications.METECControl.ExperimentDesigner.ActionsConfigWidget import ActionsConfigWidget
from Applications.METECControl.ExperimentDesigner.DesignerConfigs import ShorthandHelper
from Applications.METECControl.ExperimentDesigner.ExperimentWidgets import EditableConfig
from Utils.ExperimentUtils import verifyExperiment, experimentToDF
from Utils.FileUtils import getArgs
from Utils.FlowRateCalculator import getValveColumns

EXAMPLE_CONFIGS_PATH = os.path.join(os.path.split(__file__)[0], "./Example Configs")


class CalMenuWidget(qtw.QWidget):
    updateCalPeriods = qtc.pyqtSignal()

    def __init__(self):
        qtw.QWidget.__init__(self)
        self.check_preCalPeriod = qtw.QCheckBox()
        self.check_preCalPeriod.setText("Auto Pre Cal Period")
        self.check_preCalPeriod.stateChanged.connect(self.updateCalPeriods)
        self.check_preCalCloseSection = qtw.QCheckBox(text="Close Pre Test After Section")
        self.check_postCalCloseSection = qtw.QCheckBox(text="Close Post Test After Section")
        self.check_postCalPeriod = qtw.QCheckBox()
        self.check_postCalPeriod.setText("Auto Post Cal Period")
        self.check_postCalPeriod.stateChanged.connect(self.updateCalPeriods)

        self.select_CalOnPeriod = qtw.QSpinBox()
        self.select_CalOnPeriod.setRange(1, 9999999)
        self.select_CalOnPeriod.setValue(180)
        self.select_CalOffPeriod = qtw.QSpinBox()
        self.select_CalOffPeriod.setRange(1, 9999999)
        self.select_CalOffPeriod.setValue(60)

        layout = qtw.QGridLayout()
        self.setLayout(layout)
        layout.addWidget(self.check_preCalPeriod, 0, 1, 1, 2)
        layout.addWidget(self.check_postCalPeriod, 1, 1, 1, 2)
        layout.addWidget(qtw.QLabel(text="ON Period (sec.)"), 2, 1)
        layout.addWidget(qtw.QLabel(text="OFF Period (sec.)"), 3, 1)
        layout.addWidget(self.select_CalOnPeriod, 2, 2)
        layout.addWidget(self.select_CalOffPeriod, 3, 2)
        layout.addWidget(self.check_preCalCloseSection, 4, 1, 1, 2)
        layout.addWidget(self.check_postCalCloseSection, 5, 1, 1, 2)

    def getOnTiming(self):
        return self.select_CalOnPeriod.value()

    def getOffTiming(self):
        return self.select_CalOffPeriod.value()

    def getPreChecked(self):
        return self.check_preCalPeriod.isChecked()

    def getPostChecked(self):
        return self.check_postCalPeriod.isChecked()

    def getPreCloseSection(self):
        return self.check_preCalCloseSection.isChecked()

    def getPostCloseSection(self):
        return self.check_postCalCloseSection.isChecked()


class ExperimentDesigner:
    """
    Design experiments after loading ep, fm, spans configs and assigning pressure values
    Options:
        -d : debug mode, automatically loads some example config files
        -savedir [PATH] : default directory for saving experiments, configs, and event tables.
    """

    def __init__(self, svnPath="D:\SVNs\METEC_SVN", saveDir=None, debug=False, confirm=False):
        layout = qtw.QGridLayout()
        self.fileSelector = FileSelector()
        self.menubar = qtw.QMenuBar()
        self.savedir = saveDir if saveDir else os.path.abspath(os.path.join(os.path.split(__file__)[0], './savedata'))
        if not os.path.exists(self.savedir):
            os.mkdir(self.savedir)
        # parser = OptionParser()
        # parser.add_option("-s", "--savedir", dest="savedir",
        #                   help="change savedata directory (defaults to ./ExperimentDesigner/savedata", metavar="FILE")
        # parser.add_option("-d", "--debug",
        #                   action="store_true", dest="debug", default=False,
        #                   help="automatically load some example configs")
        # (options, args) = parser.parse_args()
        # self.savedir = options.savedir


        if confirm:
            self.mainWindow = qtw.QDialog()
            self.mainWindow.setWindowTitle("Experiment Designer")
            self.mainWindow.setGeometry(100, 100, 1500, 1000)
            self.mainWindow.setLayout(layout)
            layout.setMenuBar(self.menubar)
        else:
            self.mainWindow = qtw.QMainWindow()
            self.mainWidget = qtw.QWidget()
            self.mainWindow.setGeometry(100, 100, 1500, 1000)
            self.mainWindow.setCentralWidget(self.mainWidget)
            self.mainWindow.setMenuBar(self.menubar)
            self.mainWidget.setLayout(layout)
        self.experimentMsg = qtw.QMessageBox()
        #calmenu
        calMenu = self.menubar.addMenu("Cal Periods")
        self.calMenuWidget = CalMenuWidget()
        calwidgetaction = qtw.QWidgetAction(self.menubar)
        calwidgetaction.setDefaultWidget(self.calMenuWidget)
        calMenu.addAction(calwidgetaction)
        calMenu.aboutToHide.connect(self.updateCalPeriods)
        self.calOnTime = 180
        self.calOffTime = 60
        self.updateCal = False

        def setUpdateCal(x):
            self.updateCal = x

        self.calMenuWidget.updateCalPeriods.connect(lambda: setUpdateCal(True))

        self.actionsConfigWidget = ActionsConfigWidget(self.menubar, savedir=self.savedir)
        self.actionsConfigWidget.durationsChanged.connect(self.slot_durationsChanged)
        # tabwidget
        self.configsTabWidget = qtw.QTabWidget()
        # self.configsTabWidget.setFixedWidth(320)
        # todo: check if this broke anything.
        #  note: moved config_fm setting up before ep setting up. Was directly after.
        self.config_fm = EditableConfig(["Controller", "Row", "Flowmeter ID"], hiddenColumns=['Row'])
        self.config_fm.loadFile.connect(lambda: self.loadFile(self.config_fm, "FM Config",
                                                              defaultDir=os.path.join(svnPath,
                                                                                      "Facility Operations\\ConfigurationAndCalibrationRecords\\FlowMeterConfigurations")))
        self.configsTabWidget.addTab(self.config_fm, 'FM')
        self.config_ep = EditableConfig(["Emission Point", "Shorthand", "Column", "Description",'Row'], hiddenColumns=["Column",'Row'])
        self.config_ep.loadFile.connect(lambda: self.loadFile(self.config_ep, "EP Config", defaultDir=os.path.join(svnPath, "Facility Operations\\ConfigurationAndCalibrationRecords\\EmissionPointConfigurations")))
        self.configsTabWidget.addTab(self.config_ep, 'EP')
        self.config_spans = EditableConfig(["Flow Name", "Orifice"])
        self.config_spans.loadFile.connect(lambda: self.loadFile(self.config_spans, "Spans Config", defaultDir=os.path.join(svnPath, "Facility Operations\\ConfigurationAndCalibrationRecords\\ReaderRecords")))
        # self.config_spans.edited.connect(lambda: self.configChanged(self.config_spans))
        self.configsTabWidget.addTab(self.config_spans, 'Spans')
        self.config_pressures = EditableConfig(["Controller", "Pressure (psia)"])
        self.config_pressures.loadFile.connect(lambda: self.loadFile(self.config_pressures, "Pressures Config"))
        # self.config_pressures.edited.connect(lambda: self.configChanged(self.config_pressures))
        self.configsTabWidget.addTab(self.config_pressures, 'Pressures')

        button_saveConfigs = qtw.QPushButton(text="Save Configs")
        button_saveConfigs.clicked.connect(self.saveConfigs)
        button_loadConfigs = qtw.QPushButton(text="Load Configs")
        button_loadConfigs.clicked.connect(self.loadConfigs)

        label_temp = qtw.QLabel("T<sub>1</sub> (℉)")
        label_atm = qtw.QLabel("P<sub>2</sub> (psia)")
        label_sg = qtw.QLabel("S.G.")
        label_kFactor = qtw.QLabel("K Rel N<sub>2</sub>")

        self.select_temp = qtw.QDoubleSpinBox()
        self.select_temp.setSingleStep(0.5)
        self.select_temp.setFixedWidth(100)
        self.select_temp.setDecimals(1)
        self.select_temp.setValue(70)
        self.select_sg = qtw.QDoubleSpinBox()
        self.select_sg.setSingleStep(0.001)
        self.select_sg.setFixedWidth(100)
        self.select_sg.setDecimals(3)
        self.select_sg.setValue(0.554)
        self.select_atm = qtw.QDoubleSpinBox()
        self.select_atm.setSingleStep(0.5)
        self.select_atm.setFixedWidth(100)
        self.select_atm.setDecimals(1)
        self.select_atm.setValue(12.5)
        self.select_kFactor = qtw.QDoubleSpinBox()
        self.select_kFactor.setSingleStep(0.01)
        self.select_kFactor.setMinimumWidth(100)
        self.select_kFactor.setDecimals(3)
        self.select_kFactor.setValue(0.75)
        self.refreshButton = qtw.QPushButton(text="Refresh flow rates")
        self.refreshButton.clicked.connect(self.refreshFlowRates)
        self.select_iterations = qtw.QSpinBox()
        self.select_iterations.setRange(1, 999)
        self.select_iterations.valueChanged.connect(lambda x: self.slot_durationsChanged(int(self.showPreCalDir.text()),
                                                    int(self.showOneIterationDir.text()), int(self.showPostCalDir.text())))
        self.showPreCalDir = qtw.QLabel(text="")
        self.showOneIterationDir = qtw.QLabel(text="")
        self.showPostCalDir = qtw.QLabel(text="")
        self.showSectionDir = qtw.QLabel(text="")
        self.select_closeSection = qtw.QCheckBox(text="Close after \nsection")
        self.select_closeIteration = qtw.QCheckBox(text="Close after \neach iteration")

        self.button_loadExperiment = qtw.QPushButton(text="Load Experiment")
        self.button_loadExperiment.clicked.connect(self._pickExperimentJson)
        self.button_saveExperiment = qtw.QPushButton(text="Save Experiment")
        self.button_saveExperiment.clicked.connect(self.saveExperimentFile)
        self.confirmed = False
        self.button_confirmExperiment = qtw.QPushButton(text="Confirm")
        self.button_confirmExperiment.clicked.connect(self._setConfirmed)

        constantsWidget = qtw.QGroupBox(title="Flow Calculation Constants")
        constantsLayout = qtw.QGridLayout()
        constantsWidget.setLayout(constantsLayout)
        constantsLayout.addWidget(label_temp, 1, 1, alignment=qtc.Qt.AlignRight)
        constantsLayout.addWidget(self.select_temp, 1, 2, alignment=qtc.Qt.AlignLeft)
        constantsLayout.addWidget(label_atm, 3, 1, alignment=qtc.Qt.AlignRight)
        constantsLayout.addWidget(self.select_atm, 3, 2, alignment=qtc.Qt.AlignLeft)
        constantsLayout.addWidget(label_sg, 2, 1, alignment=qtc.Qt.AlignRight)
        constantsLayout.addWidget(self.select_sg, 2, 2, alignment=qtc.Qt.AlignLeft)
        constantsLayout.addWidget(label_kFactor, 4, 1, alignment=qtc.Qt.AlignRight)
        constantsLayout.addWidget(self.select_kFactor, 4, 2, alignment=qtc.Qt.AlignLeft)

        optionsWidget = qtw.QGroupBox(title="Experiment Options")
        optionsLayout = qtw.QGridLayout()
        optionsWidget.setLayout(optionsLayout)
        optionsLayout.addWidget(qtw.QLabel("Iterations"), 1, 1)
        optionsLayout.addWidget(self.select_iterations, 1, 2, alignment=qtc.Qt.AlignLeft)
        optionsLayout.addWidget(qtw.QLabel("Pre Cal Δt"), 2, 1, alignment=qtc.Qt.AlignRight)
        optionsLayout.addWidget(self.showPreCalDir, 2, 2)
        optionsLayout.addWidget(qtw.QLabel("1 Iteration Δt"), 3, 1, alignment=qtc.Qt.AlignRight)
        optionsLayout.addWidget(self.showOneIterationDir, 3, 2)
        optionsLayout.addWidget(qtw.QLabel("Pre Cal Δt"), 4, 1, alignment=qtc.Qt.AlignRight)
        optionsLayout.addWidget(self.showPostCalDir, 4, 2)
        optionsLayout.addWidget(qtw.QLabel("Section Δt"), 5, 1, alignment=qtc.Qt.AlignRight)
        optionsLayout.addWidget(self.showSectionDir, 5, 2)
        optionsLayout.addWidget(self.select_closeSection, 6, 1, 1, 2)
        optionsLayout.addWidget(self.select_closeIteration, 7, 1, 1, 2)

        layout.addWidget(self.configsTabWidget, 1, 1, 3, 2)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 8)
        layout.addWidget(button_saveConfigs, 4, 1, 1, 1)
        layout.addWidget(button_loadConfigs, 4, 2)
        layout.addWidget(constantsWidget, 5, 1, 1, 1)
        layout.addWidget(optionsWidget, 5, 2, 1, 1)
        layout.addWidget(self.refreshButton, 6, 1, 1, 2)
        layout.addWidget(self.button_saveExperiment, 7, 2, 1, 1)
        layout.addWidget(self.actionsConfigWidget, 1, 3, 6, 5)
        if confirm:
            layout.addWidget(self.button_confirmExperiment, 7, 1, 1, 1)
            self.loadExperimentFile(confirm)
        else:
            layout.addWidget(self.button_loadExperiment, 7, 1, 1, 1)

        ########### enable debug mode to add example configs
        if debug:
            self.loadFile(self.config_ep, "", str(pathlib.Path("D:\SVN_METEC\Facility Operations\ConfigurationAndCalibrationRecords\EmissionPointConfigurations\EmissionPointConfig-20230514-AppliedRplumeUpside.xlsx")))
            self.loadFile(self.config_fm, "", str(pathlib.Path("D:\SVN_METEC\Facility Operations\ConfigurationAndCalibrationRecords\FlowMeterConfigurations\FlowMeterConfig20240110_GH-1_Updated.xlsx")))
            self.loadFile(self.config_spans, "", str(pathlib.Path("D:\SVN_METEC\Facility Operations\ConfigurationAndCalibrationRecords\ReaderRecords\SiteConfig-20231128.json")))
            self.config_pressures.view.model()._df['Pressure (psia)'] = 50
            self.config_pressures.view.resizeColumnsToContents()
        # self.refreshFlowRates()
    def _setConfirmed(self):
        self.confirmed = True
        self.mainWindow.accept()

    def getConfirmedExperiment(self):
        confirmed = self.mainWindow.exec()
        if confirmed:
            confirmed = self.getExperimentDict()
            return confirmed
        else:
            return None

    def getExperimentDict(self):
        fmDF = self.config_fm.getExperimentConfigData()
        epDF = self.config_ep.getExperimentConfigData()
        pressuresDF = self.config_pressures.getExperimentConfigData()
        spansDF = self.config_spans.getExperimentConfigData()
        actionsDF = self.actionsConfigWidget.getActions().sort_values("Timing")
        postCalStartTime = int(self.actionsConfigWidget.getPostCalStartTime())
        postCalEvents = self.actionsConfigWidget.getPostCalEvents()
        preCalEvents = self.actionsConfigWidget.getPreCalEvents()
        expDF = actionsDF.loc[(~actionsDF.index.isin(postCalEvents)) & (~actionsDF.index.isin(preCalEvents))]
        preExpDF = actionsDF.copy().loc[actionsDF.index.isin(preCalEvents)]
        postExpDF = actionsDF.copy().loc[actionsDF.index.isin(postCalEvents)]
        try:
            #### metadata
            reqEPs = list(expDF["Emission Point"].unique())
            reqControllers = set()
            for ep in reqEPs:
                try:
                    shorthand = epDF.loc[epDF['Emission Point'] == ep, 'Shorthand'].item()
                    cb = ShorthandHelper(shorthand).cb
                    reqControllers.add(cb)
                    fm = fmDF.loc[fmDF['Controller'] == cb, "Flowmeter ID"].item()
                    if fm:
                        reqControllers.add(fm)
                except:
                    pass
            fmDF = fmDF.loc[fmDF['Controller'].isin(reqControllers)]
            epDF = epDF.loc[epDF['Emission Point'].isin(reqEPs)]
            fmDict = dict(zip(fmDF['Controller'], fmDF['Flowmeter ID']))
            epDict = dict(zip(epDF["Emission Point"], epDF['Shorthand']))
            epMaxColumnDict = dict(zip(epDF['Emission Point'], epDF['Column']))
            pressuresDF = pressuresDF.loc[pressuresDF['Controller'].isin(reqControllers)]
            pressuresDict = dict(zip(pressuresDF[self.config_pressures.columns[0]], pd.to_numeric(pressuresDF[self.config_pressures.columns[1]])))
            spansDF['cb'] = [a.split(".")[0] for a in spansDF['Flow Name']]
            spansDF = spansDF.loc[(spansDF['cb'].isin(reqControllers)) | (spansDF['Flow Name'].isin(reqControllers))]
            spanDict = dict(zip(spansDF['Flow Name'], spansDF["Orifice"]))
            curUnit = self.actionsConfigWidget.select_unit.currentText() if self.actionsConfigWidget.select_unit.currentText() else "SLPM"
            epStats = self.actionsConfigWidget.calculateFlowRateStats(expDF, curUnit)
            preExpLength, postExpLength = None, None
            if len(preCalEvents) > 0:
                preExpLength = abs(int(preExpDF['Timing'].min()))
            if len(postCalEvents) > 0:
                postExpLength = int(postExpDF['Timing'].max()-postCalStartTime)
            preExpDF['Timing'] += preExpLength
            postExpDF['Timing'] -= postCalStartTime

            experimentDict = {
                "Metadata": {
                    "FMConfig": fmDict,
                    "EPConfig": epDict,
                    'EPMaxColumn': epMaxColumnDict,
                    "Spans": spanDict,
                    "Pressures (psia)": pressuresDict,
                    "EPStats": epStats,
                    "PreExperimentLength (sec)": preExpLength,
                    "ExperimentLength (sec)": postCalStartTime,
                    "PostExperimentLength (sec)": postExpLength,
                    "ConfigValues": {
                        "T1 (F)": self.select_temp.value(),
                        "P2 (psia)": self.select_atm.value(),
                        "SG": self.select_sg.value(),
                        "K Rel N2": self.select_kFactor.value()
                    }
                }
            }
            ##### actions
            if len(preCalEvents) > 0:
                experimentDict['PreExperiment'] = {
                    "CloseAfterSection": self.calMenuWidget.getPreCloseSection(),
                    "ControlledReleases": self.buildControlledReleases(preExpDF)
                }
            experimentDict['Experiment'] = {
                "Iterations": self.select_iterations.value(),
                "CloseAfterSection": self.select_closeSection.isChecked(),
                "CloseAfterIteration": self.select_closeIteration.isChecked(),
                "ControlledReleases": self.buildControlledReleases(expDF)
            }
            if len(postCalEvents) > 0:
                experimentDict['PostExperiment'] = {
                    "CloseAfterSection": self.calMenuWidget.getPostCloseSection(),
                    "ControlledReleases": self.buildControlledReleases(postExpDF)
                }
            verifyExperiment(experimentDict)
            return experimentDict
        except Exception as e:
            print(e)
            self.experimentMsg.setText(f"Cannot create Experiment due to error:\n"+str(e))
            self.experimentMsg.exec()
            raise e

    def saveExperimentFile(self):
        experimentDict = self.getExperimentDict()
        self.fileSelector.filepath = ".json"
        self.fileSelector.viewJson(experimentDict, confirm=False, editable=True, filepath=".json")

    def buildControlledReleases(self, df: pd.DataFrame):
        releases = []
        for i, timeEvents in df.groupby("Timing"):
            release = {
                'Time': int(timeEvents['Timing'].values[0]),
                'Actions': []
            }
            for eid, event in timeEvents.iterrows():
                epDF = self.config_ep.getExperimentConfigData()
                epConfigs = epDF.loc[epDF['Emission Point'] == event['Emission Point']]
                shorthand = epConfigs['Shorthand'].item()
                shHelper = ShorthandHelper(shorthand)
                cb = shHelper.cb
                row = shorthand.split('-')[1][0]
                maxColumn = int(epConfigs['Column'].item())
                columns = getValveColumns(event['Flow Level'])
                ab = shorthand.split('-')[1][1]
                if ab == 'B':
                    lastColumnState = 0
                else:
                    lastColumnState = 1
                setStates = {}
                for col in range(1,maxColumn):
                    if col in columns:
                        setStates['EV-'+str(row)+str(col)] = 0
                    else:
                        setStates['EV-'+str(row)+str(col)] = 1
                setStates['EV-'+str(row)+str(maxColumn)] = lastColumnState
                action = {
                    'ActionType': "Defined",
                    'EmissionPoint': event['Emission Point'],
                    'FlowLevel': event['Flow Level'],
                    'Controller': cb,
                    "EmissionCategory": event['Emission Category'],
                    "Intent": event['Intent'],
                    'SetStates': setStates
                }
                release['Actions'].append(action)
            releases.append(release)
        return releases

    def _pickExperimentJson(self):
        filepath, filters = qtw.QFileDialog.getOpenFileName(None, "load Experiment Json", "", filter="*.json")
        if filepath:
            self.loadExperimentFile(filepath)

    def loadExperimentFile(self, filepath):
        try:
            with open(filepath, "r") as f:
                experimentConfig = json.load(f)
            self.actionsConfigWidget.clearTable()
            metadata = experimentConfig.get("Metadata")
            experiment=experimentConfig.get("Experiment")
            self.select_closeIteration.setChecked(experiment.get("CloseAfterIteration"))
            self.select_closeSection.setChecked(experiment.get("CloseAfterSection"))
            self.select_iterations.setValue(experiment.get("Iterations"))
            preExperiment = experimentConfig.get("PreExperiment")
            if preExperiment:
                self.calMenuWidget.check_preCalCloseSection.setChecked(preExperiment.get("CloseAfterSection"))
            postExperiment = experimentConfig.get("PostExperiment")
            if postExperiment:
                self.calMenuWidget.check_postCalCloseSection.setChecked(postExperiment.get("CloseAfterSection"))
            epconfig = metadata.get("EPConfig")
            epcolumn = metadata.get("EPMaxColumn")
            # combine epcolumn and epconfig into one dataframe
            epdata = []
            for ep, shorthand in epconfig.items():
                epdata.append([ep, shorthand, epcolumn.get(ep), ""])
            self.config_ep.setData(epdata)
            self.config_fm.setData(metadata.get("FMConfig"))
            self.config_spans.setData(metadata.get("Spans"))
            self.config_pressures.setData(metadata.get("Pressures (psia)"))
            self.actionsConfigWidget.setEPConfig(self.config_ep.getExperimentConfigData())
            self.actionsConfigWidget.setFMConfig(self.config_fm.getExperimentConfigData())
            self.actionsConfigWidget.setPressuresConfig(self.config_pressures.getExperimentConfigData())
            self.actionsConfigWidget.setOrificeConfig(self.config_spans.getExperimentConfigData())
            df = experimentToDF(experimentConfig)
            self.actionsConfigWidget.table.setDF(df)
            self.actionsConfigWidget.resetIDs()
        except Exception as e:
            msg = qtw.QMessageBox()
            msg.setText("Error loading experiment config:\n"+str(e))
            msg.exec()

    def loadFile(self, editableConfig: EditableConfig, channelName, filepath=None, defaultDir=""):
        if filepath is None:
            filepath = self.fileSelector.chooseFile(channelName, defaultDir=defaultDir)
        if filepath:
            try:
                df, spansJson = None, None
                if filepath.endswith('.xlsx'):
                    df = pd.read_excel(filepath)
                elif filepath.endswith('.csv'):
                    df = pd.read_csv(filepath)
                elif filepath.endswith(".json"):
                    with open(filepath, "r") as f:
                        spansJson = json.load(f)
                else:
                    raise Exception(f"File type incorrect for config")
                if editableConfig == self.config_spans: # spans
                    if df is not None:
                        if 'name' in df.columns and 'max' in df.columns:
                            df = df.get(["name", "max", "item_type"])
                            if "name" in df.columns and "max" in df.columns:
                                df = df.loc[(df['item_type'] == "Electric Valve") | (df['item_type'] == "Flow Meter")]
                                df = df.rename(columns={"name": "Flow Name", "max": "Orifice"}).get(["Flow Name", "Orifice"])
                    if spansJson:
                        spansData = {"Flow Name":[], "Orifice":[]}
                        for key, value in spansJson.items():
                            fields = value['fields']
                            for name, evdata in fields.items():
                                if "EV" in name:
                                    spansData['Flow Name'].append(name)
                                    spansData['Orifice'].append(evdata.get("orifice_size"))
                                if "FM" in name:
                                    spansData['Flow Name'].append(name)
                                    spansData['Orifice'].append(evdata.get("max"))
                        df = pd.DataFrame.from_dict(spansData)
                    self.actionsConfigWidget.setOrificeConfig(df)
                if editableConfig == self.config_fm: # fm
                    df = df.get(self.config_fm.columns)
                    pressuresDF = pd.DataFrame(df[~df["Controller"].duplicated()].get('Controller'))
                    pressuresDF = pressuresDF.reset_index(drop=True)
                    pressuresDF[self.config_pressures.columns[1]] = 0
                    oldPressuresDF = self.config_pressures.getExperimentConfigData()
                    if oldPressuresDF is not None:
                        # todo: check that changing pressuresDF from series to DF didn't break this.
                        for index, row in pressuresDF.iterrows():
                            try:
                                pressure = oldPressuresDF.loc[oldPressuresDF['Controller'] == row['Controller'], self.config_pressures.columns[1]].item()
                                pressuresDF.loc[index, self.config_pressures.columns[1]] = pressure
                            except ValueError:
                                pass
                    self.config_pressures.setData(pressuresDF)
                    self.actionsConfigWidget.setFMConfig(df)
                    self.actionsConfigWidget.setPressuresConfig(self.config_pressures.getExperimentConfigData())
                if editableConfig == self.config_ep: #ep
                    self.actionsConfigWidget.setEPConfig(df)
                if editableConfig == self.config_pressures:
                    # df = df.get(self.config_pressures.columns)
                    self.actionsConfigWidget.setPressuresConfig(df)
                editableConfig.setFilepath(filepath)
                editableConfig.setData(df)
            except Exception as e:
                error = qtw.QMessageBox()
                error.setText(f"Error loading config due to {type(e)} error: {e}")
                error.exec()


    def updateCalPeriods(self):
        if self.updateCal or self.calMenuWidget.getOnTiming() != self.calOnTime and self.calMenuWidget.getOffTiming() != self.calOffTime:
            self.updateCal = False
            self.actionsConfigWidget.setCalPeriod(self.calMenuWidget.getPreChecked(), self.calMenuWidget.getPostChecked(),
                                                  self.calMenuWidget.getOnTiming(), self.calMenuWidget.getOffTiming())

    def refreshFlowRates(self):
        self.actionsConfigWidget.setEPConfig(self.config_ep.getExperimentConfigData())
        self.actionsConfigWidget.setFMConfig(self.config_fm.getExperimentConfigData())
        self.actionsConfigWidget.setOrificeConfig(self.config_spans.getExperimentConfigData())
        self.actionsConfigWidget.setPressuresConfig(self.config_pressures.getExperimentConfigData())
        self.actionsConfigWidget.setConfigValues(self.select_atm.value(), self.select_temp.value(), self.select_sg.value(), self.select_kFactor.value())
        self.actionsConfigWidget.refreshFlowRates()

    # @qtc.pyqtSlot(object)
    def configChanged(self, config):
        if config is self.config_pressures:
            self.actionsConfigWidget.setPressuresConfig(self.config_pressures.getExperimentConfigData())
        if config is self.config_spans:
            self.actionsConfigWidget.setOrificeConfig(self.config_spans.getExperimentConfigData())
        self.actionsConfigWidget.refreshFlowRates()

    def slot_durationsChanged(self, preExpDir, expDir, postExpDir):
        self.showPreCalDir.setText(str(preExpDir))
        self.showOneIterationDir.setText(str(expDir))
        self.showPostCalDir.setText(str(postExpDir))
        self.showSectionDir.setText(str(expDir*self.select_iterations.value()))

    def saveConfigs(self):
        epdf = self.config_ep.getExperimentConfigData()
        fmdf = self.config_fm.getExperimentConfigData()
        spansdf = self.config_spans.getExperimentConfigData()
        pressuresdf = self.config_pressures.getExperimentConfigData()
        path = self.fileSelector.fileDialog.getExistingDirectory(self.mainWidget, 'Save Configs', os.path.abspath(self.savedir))
        if path:
            epdf.to_csv(os.path.join(path,"ep.csv"), index=False)
            fmdf.to_csv(os.path.join(path, "fm.csv"), index=False)
            spansdf.to_csv(os.path.join(path, "spans.csv"), index=False)
            pressuresdf.to_csv(os.path.join(path, "pressures.csv"), index=False)

    def loadConfigs(self, path=None):
        if not path:
            path = self.fileSelector.fileDialog.getExistingDirectory(self.mainWidget, 'Load Configs', os.path.abspath(self.savedir))
        if path:
            try:
                self.loadFile(self.config_ep, 'EP Config', os.path.join(path, "ep.csv"))
                self.loadFile(self.config_fm, 'FM Config', os.path.join(path, "fm.csv"))
                self.loadFile(self.config_spans, 'Spans', os.path.join(path, "spans.csv"))
                self.loadFile(self.config_pressures, 'Pressures', os.path.join(path, "pressures.csv"))
            except Exception as e:
                print(e)

class FileSelector(qtc.QObject):

    def __init__(self, parent=None):
        qtc.QObject.__init__(self, parent)
        self.filepath = None
        self.currentConfig = None

        self.fileDialog = qtw.QFileDialog()
        self.popout = qtw.QDialog()
        self.popout.setGeometry(100, 100, 1000, 800)
        self.popout.setLayout(qtw.QGridLayout())
        self.pathLabel = qtw.QLabel(text="Path: ")
        self.plainTextView = qtw.QPlainTextEdit(None)
        self.plainTextView.setReadOnly(False)
        self.currentView = self.plainTextView
        self.popout.layout().addWidget(self.pathLabel, 1, 1)
        self.popout.layout().addWidget(self.currentView, 2, 1)

        self.confirmButtons = qtw.QWidget()
        self.confirmButtons.setLayout(qtw.QHBoxLayout())
        self.confirmButtons.buttonConfirm = qtw.QPushButton(text="Confirm")
        self.confirmButtons.buttonLoadNew = qtw.QPushButton(text="Load New")
        self.confirmButtons.layout().addWidget(self.confirmButtons.buttonLoadNew)
        self.confirmButtons.layout().addWidget(self.confirmButtons.buttonConfirm)
        self.confirmButtons.buttonConfirm.clicked.connect(self.popout.accept)
        self.confirmButtons.buttonLoadNew.clicked.connect(self._clicked_loadNew)

        self.editButtons = qtw.QWidget()
        self.editButtons.setLayout(qtw.QHBoxLayout())
        self.editButtons.buttonExport = qtw.QPushButton(text="Export")
        self.editButtons.layout().addWidget(self.editButtons.buttonExport)
        self.editButtons.buttonExport.clicked.connect(lambda x: self.saveView(self.filepath, self.currentView))

    def viewJson(self, dictionary, confirm=False, editable=False, filepath=None):
        if editable:
            self._addEditButtons()
        if confirm:
            confirmButton = qtw.QPushButton(text="Confirm")
            confirmButton.clicked.connect(self.popout.accept)
            self.popout.layout().addWidget(confirmButton, 4, 1)
        self.popout.setWindowTitle("Experiment")
        self.filepath = filepath
        self.pathLabel.setText("")
        view = qtw.QPlainTextEdit()
        view.appendPlainText(json.dumps(dictionary, indent=2))
        view.setReadOnly(not editable)
        if type(dictionary) is dict:
            self._swapViewWidget(view)
            ret = self.popout.exec()
        if confirm:
            self.popout.layout().removeWidget(confirmButton)
            confirmButton.setParent(None)
            confirmButton.deleteLater()
        if editable:
            self._removeEditButtons()
        return ret

    def viewFile(self, filepath, configName):
        self.popout.setWindowTitle(configName)
        self.currentConfig = configName
        if self._updateFileView(filepath):
            self.popout.exec()

    def confirmConfig(self, filepath, configName):
        self.popout.setWindowTitle(configName)
        self.currentConfig = configName
        if self._updateFileView(filepath):
            self._addConfirmButtons()
            ret = self.popout.exec()
            self._removeConfirmButtons()
            return ret

    def editConfig(self, filepath, configName):
        self.popout.setWindowTitle(configName)
        self.currentConfig = configName
        if self._updateFileView(filepath, editable=True):
            self._addEditButtons()
            self.popout.exec()
            self._removeEditButtons()

    def chooseFile(self, configName, defaultDir=""):
        filepath, filters = self.fileDialog.getOpenFileName(None, "load config " + configName, defaultDir)
        if self.confirmConfig(filepath, configName):
            return self.filepath

    def _clicked_loadNew(self):
        filepath, filters = self.fileDialog.getOpenFileName(None, "load config "+str(self.currentConfig), "")
        if filepath:
            self._updateFileView(filepath)

    def _updateFileView(self, filepath, editable=False):
        self.filepath = filepath
        self.pathLabel.setText("Path: "+filepath)
        if os.path.exists(filepath):
            view = self.getView(filepath, editable)
            self._swapViewWidget(view)
            return True
        else:
            msg = qtw.QMessageBox()
            msg.setText('Can not load config "'+self.currentConfig+ '"\nPath "' + filepath + '" not found')
            msg.exec()
            return False

    @staticmethod
    def saveView(oldfilepath, currentView):
        filedialog = qtw.QFileDialog()
        filedialog.setAttribute(qtc.Qt.WA_DeleteOnClose)
        if oldfilepath:
            filter = oldfilepath.split(".")[-1]
        else:
            filter=".json"
        filter = "(*."+filter+")"
        filepath, filters = filedialog.getSaveFileName(None, "Save config", oldfilepath, filter)
        if filepath:
            if type(currentView) is qtw.QPlainTextEdit:
                with open(filepath, "w") as f:
                    f.write(currentView.toPlainText())
            elif type(currentView) is qtw.QTableView:
                currentView.model().getDataFrame().to_excel(filepath, index=False)

    @staticmethod
    def getView(filepath, editable):
        if os.path.exists(filepath):
            if filepath.endswith((".csv", ".xlsx")):
                try:
                    view = FileSelector.getDataFrameView(filepath, editable)
                    view.resizeColumnsToContents()
                    return view
                except:
                    pass
            if editable not in (False, None):
                editable = True
            return FileSelector.getPlainTextView(filepath, editable)
        else:
            msg = qtw.QMessageBox()
            msg.setText('Can not load path: "' + filepath)
            msg.exec()
            return False

    @staticmethod
    def getDataFrameView(filepath:str, editableColumns=None):
        view = qtw.QTableView()
        if filepath.endswith(".xlsx"):
            df = pd.read_excel(filepath)
        if filepath.endswith(".csv"):
            with open(filepath) as f:
                dialect = csv.Sniffer().sniff(f.readline())
                df = pd.read_csv(filepath, dialect=dialect)
        model = DataFrameModel(df, editableColumns=editableColumns)
        view.setModel(model)
        return view

    @staticmethod
    def getPlainTextView(filepath, editable=False):
        text= qtw.QPlainTextEdit()
        text.setReadOnly(not editable)
        with open(filepath, "r") as f:
            for line in f:
                text.appendPlainText(line)
        return text

    def _swapViewWidget(self, view):
        self.currentView.setParent(None)
        self.popout.layout().removeWidget(self.currentView)
        self.popout.layout().addWidget(view, 2, 1)
        view.setParent(self.popout)
        self.currentView.deleteLater()
        self.currentView = view

    def _addConfirmButtons(self):
        self.popout.layout().addWidget(self.confirmButtons, 3, 1)

    def _removeConfirmButtons(self):
        self.popout.layout().removeWidget(self.confirmButtons)
        self.confirmButtons.setParent(None)

    def _addEditButtons(self):
        self.popout.layout().addWidget(self.editButtons, 3, 1)

    def _removeEditButtons(self):
        self.popout.layout().removeWidget(self.editButtons)
        self.editButtons.setParent(None)

if __name__ == '__main__':
    # testExperimentConfigGUI()
    import sys

    ARGS_METADATA = {
        'description': 'Experiment Designer',
        'args': [
            {
                'name_or_flags': ['-m', '--metecsvn'],
                'default': "D:\SVNs\METEC_SVN",
                'help': 'Path to the METEC SVN'},
            {
                     'name_or_flags': ['-s', '--savedir'],
                     'metavar': 'FILE',
                     'dest': 'savedir',
                     'help': "change savedata directory (defaults to ./ExperimentDesigner/savedata"
            },
            {
                     'name_or_flags': ['-d', '--debug'],
                     'action': 'store_true',
                     'dest': 'debug',
                     'default': False,
                     'help': "automatically load some example configs"
            }
            ]}

    commandLineArgs = getArgs(ARGS_METADATA)
    app = qtw.QApplication(sys.argv)
    cmg = ExperimentDesigner(commandLineArgs.metecsvn, commandLineArgs.savedir, commandLineArgs.debug)
    cmg.mainWindow.show()
    sys.exit(app.exec_())


class FileSelector(qtc.QObject):

    def __init__(self, parent=None):
        qtc.QObject.__init__(self, parent)
        self.filepath = None
        self.currentConfig = None

        self.fileDialog = qtw.QFileDialog()
        self.popout = qtw.QDialog()
        self.popout.setGeometry(100, 100, 1000, 800)
        self.popout.setLayout(qtw.QGridLayout())
        self.pathLabel = qtw.QLabel(text="Path: ")
        self.plainTextView = qtw.QPlainTextEdit(None)
        self.plainTextView.setReadOnly(False)
        self.currentView = self.plainTextView
        self.popout.layout().addWidget(self.pathLabel, 1, 1)
        self.popout.layout().addWidget(self.currentView, 2, 1)

        self.confirmButtons = qtw.QWidget()
        self.confirmButtons.setLayout(qtw.QHBoxLayout())
        self.confirmButtons.buttonConfirm = qtw.QPushButton(text="Confirm")
        self.confirmButtons.buttonLoadNew = qtw.QPushButton(text="Load New")
        self.confirmButtons.layout().addWidget(self.confirmButtons.buttonLoadNew)
        self.confirmButtons.layout().addWidget(self.confirmButtons.buttonConfirm)
        self.confirmButtons.buttonConfirm.clicked.connect(self.popout.accept)
        self.confirmButtons.buttonLoadNew.clicked.connect(self._clicked_loadNew)

        self.editButtons = qtw.QWidget()
        self.editButtons.setLayout(qtw.QHBoxLayout())
        self.editButtons.buttonExport = qtw.QPushButton(text="Export")
        self.editButtons.layout().addWidget(self.editButtons.buttonExport)
        self.editButtons.buttonExport.clicked.connect(lambda x: self.saveView(self.filepath, self.currentView))

    def viewJson(self, dictionary, confirm=False, editable=False, filepath=None):
        if editable:
            self._addEditButtons()
        if confirm:
            confirmButton = qtw.QPushButton(text="Confirm")
            confirmButton.clicked.connect(self.popout.accept)
            self.popout.layout().addWidget(confirmButton, 4, 1)
        self.popout.setWindowTitle("Experiment")
        self.filepath = filepath
        self.pathLabel.setText("")
        view = qtw.QPlainTextEdit()
        view.appendPlainText(json.dumps(dictionary, indent=2))
        view.setReadOnly(not editable)
        if type(dictionary) is dict:
            self._swapViewWidget(view)
            ret = self.popout.exec()
        if confirm:
            self.popout.layout().removeWidget(confirmButton)
            confirmButton.setParent(None)
            confirmButton.deleteLater()
        if editable:
            self._removeEditButtons()
        return ret

    def viewFile(self, filepath, configName):
        self.popout.setWindowTitle(configName)
        self.currentConfig = configName
        if self._updateFileView(filepath):
            self.popout.exec()

    def confirmConfig(self, filepath, configName):
        self.popout.setWindowTitle(configName)
        self.currentConfig = configName
        if self._updateFileView(filepath):
            self._addConfirmButtons()
            ret = self.popout.exec()
            self._removeConfirmButtons()
            return ret

    def editConfig(self, filepath, configName):
        self.popout.setWindowTitle(configName)
        self.currentConfig = configName
        if self._updateFileView(filepath, editable=True):
            self._addEditButtons()
            self.popout.exec()
            self._removeEditButtons()

    def chooseFile(self, configName, defaultDir=""):
        filepath, filters = self.fileDialog.getOpenFileName(None, "load config " + configName, defaultDir)
        if self.confirmConfig(filepath, configName):
            return self.filepath

    def _clicked_loadNew(self):
        filepath, filters = self.fileDialog.getOpenFileName(None, "load config "+str(self.currentConfig), "")
        if filepath:
            self._updateFileView(filepath)

    def _updateFileView(self, filepath, editable=False):
        self.filepath = filepath
        self.pathLabel.setText("Path: "+filepath)
        if os.path.exists(filepath):
            view = self.getView(filepath, editable)
            self._swapViewWidget(view)
            return True
        else:
            msg = qtw.QMessageBox()
            msg.setText('Can not load config "'+self.currentConfig+ '"\nPath "' + filepath + '" not found')
            msg.exec()
            return False

    @staticmethod
    def saveView(oldfilepath, currentView):
        filedialog = qtw.QFileDialog()
        filedialog.setAttribute(qtc.Qt.WA_DeleteOnClose)
        if oldfilepath:
            filter = oldfilepath.split(".")[-1]
        else:
            filter=".json"
        filter = "(*."+filter+")"
        filepath, filters = filedialog.getSaveFileName(None, "Save config", oldfilepath, filter)
        if filepath:
            if type(currentView) is qtw.QPlainTextEdit:
                with open(filepath, "w") as f:
                    f.write(currentView.toPlainText())
            elif type(currentView) is qtw.QTableView:
                currentView.model().getDataFrame().to_excel(filepath, index=False)

    @staticmethod
    def getView(filepath, editable):
        if os.path.exists(filepath):
            if filepath.endswith((".csv", ".xlsx")):
                try:
                    view = FileSelector.getDataFrameView(filepath, editable)
                    view.resizeColumnsToContents()
                    return view
                except:
                    pass
            if editable not in (False, None):
                editable = True
            return FileSelector.getPlainTextView(filepath, editable)
        else:
            msg = qtw.QMessageBox()
            msg.setText('Can not load path: "' + filepath)
            msg.exec()
            return False

    @staticmethod
    def getDataFrameView(filepath:str, editableColumns=None):
        view = qtw.QTableView()
        if filepath.endswith(".xlsx"):
            df = pd.read_excel(filepath)
        if filepath.endswith(".csv"):
            with open(filepath) as f:
                dialect = csv.Sniffer().sniff(f.readline())
                df = pd.read_csv(filepath, dialect=dialect)
        model = DataFrameModel(df, editableColumns=editableColumns)
        view.setModel(model)
        return view

    @staticmethod
    def getPlainTextView(filepath, editable=False):
        text= qtw.QPlainTextEdit()
        text.setReadOnly(not editable)
        with open(filepath, "r") as f:
            for line in f:
                text.appendPlainText(line)
        return text

    def _swapViewWidget(self, view):
        self.currentView.setParent(None)
        self.popout.layout().removeWidget(self.currentView)
        self.popout.layout().addWidget(view, 2, 1)
        view.setParent(self.popout)
        self.currentView.deleteLater()
        self.currentView = view

    def _addConfirmButtons(self):
        self.popout.layout().addWidget(self.confirmButtons, 3, 1)

    def _removeConfirmButtons(self):
        self.popout.layout().removeWidget(self.confirmButtons)
        self.confirmButtons.setParent(None)

    def _addEditButtons(self):
        self.popout.layout().addWidget(self.editButtons, 3, 1)

    def _removeEditButtons(self):
        self.popout.layout().removeWidget(self.editButtons)
        self.editButtons.setParent(None)
