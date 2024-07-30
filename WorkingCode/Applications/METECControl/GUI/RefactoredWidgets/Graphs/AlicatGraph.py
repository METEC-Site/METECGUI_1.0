from Applications.METECControl.GUI.RefactoredWidgets.Graphs.BasicGraph import BasicGraph, CurveItem
from Applications.METECControl.GUI.RefactoredWidgets.Graphs.GraphLegendWidget import AlicatLegendWidget
from Utils import ClassUtils as cu

class AlicatGraph(BasicGraph):
    def __init__(self, GUIInterface,
                 name=None, parent=None,
                 *args, **kwargs):
        BasicGraph.__init__(self, GUIInterface, name, parent, *args, **kwargs)

    def addWidget(self, widget, *args, **kwargs):
        if cu.isClass(widget, CurveItem):
            plotItem = widget.getMainWidget()
            self.mainWidget.addItem(plotItem)
            name = widget.name
            label = widget.label
            wComStreams = widget.commandStreams
            wDataStreams = widget.dataStreams
            wEventStreams = widget.eventStreams
            try:
                setpt = widget.hasSetpt
            except:
                setpt=False

            legendWidget = AlicatLegendWidget(self.GUIInterface, name=name + "_legend", parent=self, unitDict=widget.unitDict, label=label, color=widget.color,
                                              commandStreams=wComStreams, dataStreams=wDataStreams, eventStreams=wEventStreams, setpt=setpt)
            legendRow = int(self.legendLocation/2) # divide by two rounded down.
            legendCol = self.legendLocation % 2 # mod 2.
            self.legendLocation += 1
            self.legendLayout.removeItem(self.legendSpacer)
            # Add the new legend item to the top left, then top right, going throuh each row sequentially.
            self.legendLayout.addWidget(legendWidget, legendRow, legendCol)
            # add a legend spacer to compactify
            self.legendLayout.addItem(self.legendSpacer, legendRow+1, 0, 1, 2)
            self.widgets[name] = {'CurveItem': widget,
                                  'LegendItem': legendWidget,
                                  'axisChange': lambda x: self.changeAxis(name, x),
                                 }
            self.legendToggle(name)
            legendWidget.axisChanged.connect(self.widgets[name]['axisChange'])

    def legendToggle(self, name):
        curveItem = self.widgets[name]['CurveItem']
        legendItem = self.widgets[name]['LegendItem']
        curveItem.toggle()
        legendItem.toggle()

    def curveColorUpdate(self, legendItem, qColor):
        corItems = list(filter(lambda x: x["LegendItem"] == legendItem, self.widgets.values()))
        corItems=corItems[0]
        curveItem = corItems["CurveItem"]
        curveItem.setColor(qColor)
