import pandas as pd
from PyQt5 import QtCore as qtc, QtGui as qtg
from PyQt5.QtCore import Qt


class DataFrameModel(qtc.QAbstractTableModel):
    edited = qtc.pyqtSignal(int, int, str)
    changedSortingColumn = qtc.pyqtSignal(str)

    def __init__(self, df:pd.DataFrame, editableColumns=False):
        qtc.QAbstractTableModel.__init__(self)
        self.setEditableColumns(editableColumns) # if None/False/emptylist then None, if list or tuple then those columns, if True then all columns
        self._df = df
        self.errorRows = []
        self.backgroundColors = {}

    def changeBackgroundColor(self, id, column, color:qtg.QColor):
        if color:
            self.backgroundColors[(id, column)] = color
        elif self.backgroundColors.get((id, column)):
            self.backgroundColors.pop((id, column))

    def clearBackgrounds(self):
        self.backgroundColors.clear()

    def rowCount(self, parent: qtc.QModelIndex = None):
        return self._df.shape[0]

    def columnCount(self, parent: qtc.QModelIndex = None):
        return self._df.shape[1]

    def data(self, index: qtc.QModelIndex, role=qtc.Qt.DisplayRole):
        row = index.row()
        col = index.column()
        if index.isValid():
            if role == qtc.Qt.DisplayRole:
                return str(self._df.iloc[row, col])
        if role == Qt.BackgroundRole:
            if self._df.iloc[row].name in self.errorRows:
                return qtg.QBrush(qtg.QColor(255, 90, 90))
            background = self.backgroundColors.get((self._df.iloc[row].name, col))
            if background:
                return qtg.QBrush(background)

    def setData(self, index: qtc.QModelIndex, value, role: int = Qt.EditRole) -> bool:
        if role == Qt.EditRole and index.isValid():
            self._df.iloc[index.row(),index.column()] = value
            self.edited.emit(index.row(), index.column(), value)
            return True
        return False

    def headerData(self, section: int, orientation: qtc.Qt.Orientation=qtc.Qt.Horizontal, role: int = qtc.Qt.DisplayRole):
        if orientation == qtc.Qt.Horizontal and role == qtc.Qt.DisplayRole:
            return self._df.columns[section]
        if role == Qt.BackgroundRole:
            return qtg.QBrush(qtg.QColor(89, 161, 96))
        if orientation == qtc.Qt.Vertical and role == qtc.Qt.DisplayRole:
            return str(section+1)
        if role == qtc.Qt.FontRole:
            boldFont = qtg.QFont()
            boldFont.setBold(True)
            return boldFont

    def flags(self, index: qtc.QModelIndex) -> Qt.ItemFlags:
        if index.isValid():
            ret = Qt.ItemIsEnabled | Qt.ItemIsSelectable
            if self.editableColumns is True:
                ret = ret | Qt.ItemIsEditable
            if type(self.editableColumns) in (list, tuple):
                if index.column() in self.editableColumns:
                    ret = ret | Qt.ItemIsEditable
            return ret

    def sort(self, column, order=None):
        order = not bool(order)
        try:
            self._df = self._df.sort_values(self._df.columns[column], ascending=order)
            self.layoutChanged.emit()
            self.changedSortingColumn.emit(self._df.columns[column])
        except TypeError:
            pass

    def getDataFrame(self, copy=False):
        if copy:
            return self._df.copy()
        else:
            return self._df

    def changeErrorIndex(self, rowIndex, error=True):
            if error:
                self.errorRows.append(rowIndex)
            else:
                try:
                    self.errorRows.remove(rowIndex)
                except:
                    pass

    def setEditableColumns(self, columns):
        self.editableColumns = columns

    def setDF(self, df):
        self._df = df
        self.endResetModel()