from Utils import TimeUtils as tu

# todo: make the GC fields match the below fields.

class ControlledRelease():

    fields = [
        'ExperimentID', 'EventID', 'ActiveEPCount',
        'EPID', 'EPLatitude', 'EPLongitude', "EmissionCategory", "EmissionIntent",
        'UTCStart', 'UTCEnd', 'Duration', "BFE", "BFU", "BFT",
        "QCFlagCount",

         'tStart', 'tTransitioned', 'tSettled', 'tEnd', 'UTCTransition', 'UTCSettled',

        'FlowmeterID', 'FlowAvg', 'FlowStDev', "FlowUncertainty", 'C1FlowAvg', 'C1FlowUncertainty', 'C2FlowAvg', 'C2FlowUncertainty', 'C3FlowAvg',
        'C3FlowUncertainty', 'C4FlowAvg', 'C4FlowUncertainty', 'THCFlowAvg', 'THCFlowUncertainty',

        "OrificeControllerID",
        'OrificeControllerPAvg', 'OrificeControllerPStd', 'OrificeControllerTAvg', 'OrificeControllerTStd',
        'EPEquipmentGroup', 'EPEquipmentUnit', 'EPDescription',  'EPAltitude',
        'EPFlowLevel', 'EPFlowSetpoint',

        'QCFlags', 'RefEventID', 'RefFlowAvg', "RefFlowUncertainty", 'RefPRatio', 'RefTRatio',

        'GCSampleCount',
        'N2MolFracAvg', 'N2MolFracStd',
        'CO2MolFracAvg', 'CO2MolFracStd',
        'C1MolFracAvg', 'C1MolFracStd',
        'C2MolFracAvg', 'C2MolFracStd',
        'C3MolFracAvg', 'C3MolFracStd',
        'iC4MolFracAvg', 'iC4MolFracStd',
        'nC4MolFracAvg', 'nC4MolFracStd',
        'iC5MolFracAvg', 'iC5MolFracStd',
        'nC5MolFracAvg', 'nC5MolFracStd',
        'C6MolFracAvg', 'C6MolFracStd',

        'KLambdaAvg', 'KLambdaStd', # average correction factor of THERMAL CONDUCTIVITY (used in thermal mass flowmeter)

        'EtaAvg',                   # average  thermal conductivity parameter calculated over the runs.

        'KEtaAvg', 'KEtaStd',       # average correction factor of ABSOLUTE VISCOSITY (used in Alicat flowmeter)
    ]

    def __init__(self, EventID=None, ExperimentID=None, QCFlagCount=None, QCFlags=None, tStart=None, tTransitioned=None, tSettled=None, tEnd=None,
                 Duration=None, UTCStart=None, UTCTransition=None, UTCSettled=None, UTCEnd=None, FlowmeterID=None, ActiveEPCount=None,

                 BFE=None, BFU=None, BFT=None,

                 FlowAvg=None, FlowStDev=None, FlowUncertainty=None, C1FlowAvg=None, C1FlowUncertainty=None,
                 C2FlowAvg=None, C2FlowUncertainty=None, C3FlowAvg=None, C3FlowUncertainty=None, C4FlowAvg=None, C4FlowUncertainty=None,
                 THCFlowAvg=None, THCFlowUncertainty=None,

                 OrificeControllerID=None,
                 OrificeControllerPAvg=None, OrificeControllerPStd=None, OrificeControllerTAvg=None,
                 OrificeControllerTStd=None, EPID=None, EPEquipmentGroup=None, EPEquipmentUnit=None,
                 EPDescription=None, EPLatitude=None, EPLongitude=None, EPAltitude=None, EPFlowLevel=None,
                 EPFlowSetpoint=None, EmissionIntent=None, EmissionCategory=None,

                 RefEventID=None, RefFlowAvg=None, RefFlowUncertainty=None, RefPRatio=None, RefTRatio=None,

                 GCSampleCount=None,
                 N2MolFracAvg=None, N2MolFracStd=None, CO2MolFracAvg=None, CO2MolFracStd=None, C1MolFracAvg=None, C1MolFracStd=None,
                 C2MolFracAvg=None, C2MolFracStd=None, C3MolFracAvg=None, C3MolFracStd=None, iC4MolFracAvg=None, iC4MolFracStd=None,
                 nC4MolFracAvg=None, nC4MolFracStd=None, iC5MolFracAvg=None, iC5MolFracStd=None, nC5MolFracAvg=None, nC5MolFracStd=None,
                 C6MolFracAvg=None, C6MolFracStd=None, KLambdaAvg=None, KLambdaStd=None, EtaAvg=None, KEtaAvg=None, KEtaStd=None):

        self.map = {k:None for k in ControlledRelease.fields}

        self.setExperimentInfo(eventID=EventID, ExperimentID=ExperimentID, QCFlagCount=QCFlagCount, QCFlags=QCFlags, tStart=tStart, tTransitioned=tTransitioned,
                               tSettled=tSettled, tEnd=tEnd, Duration=Duration, UTCStart=UTCStart,
                               UTCTransition=UTCTransition, UTCSettled=UTCSettled, UTCEnd=UTCEnd,
                               FlowmeterID=FlowmeterID, ActiveEPCount=ActiveEPCount)
        self.setFlowInfo(FlowAvg=FlowAvg, FlowStDev=FlowStDev, FlowUncertainty=FlowUncertainty, C1FlowAvg=C1FlowAvg,
                         BFE=BFE, BFU=BFU, BFT=BFT,
                         C1FlowUncertainty=C1FlowUncertainty,C2FlowAvg=C2FlowAvg, C2FlowUncertainty=C2FlowUncertainty,
                         C3FlowAvg=C3FlowAvg, C3FlowUncertainty=C3FlowUncertainty, C4FlowAvg=C4FlowAvg,
                         C4FlowUncertainty=C4FlowUncertainty, THCFlowAvg=THCFlowAvg, THCFlowUncertainty=THCFlowUncertainty)
        self.setEmissionPointInfo(OrificeControllerID=OrificeControllerID,OrificeControllerPAvg=OrificeControllerPAvg, OrificeControllerPStd=OrificeControllerPStd,
                                  OrificeControllerTAvg=OrificeControllerTAvg, OrificeControllerTStd=OrificeControllerTStd,
                                  EPID=EPID, EPEquipmentGroup=EPEquipmentGroup, EPEquipmentUnit=EPEquipmentUnit,
                                  EPDescription=EPDescription, EPLatitude=EPLatitude, EPLongitude=EPLongitude,
                                  EPAltitude=EPAltitude, EPFlowLevel=EPFlowLevel, EPFlowSetpoint=EPFlowSetpoint, EmissionIntent=EmissionIntent, EmissionCategory=EmissionCategory)
        self.setRefInfo(RefEventID=RefEventID, RefFlowAvg=RefFlowAvg, RefFlowUncertainty=RefFlowUncertainty, RefPRatio=RefPRatio, RefTRatio=RefTRatio)
        self.setGCInfo(GCSampleCount=GCSampleCount, N2MolFracAvg=N2MolFracAvg, N2MolFracStd=N2MolFracStd, CO2MolFracAvg=CO2MolFracAvg,
                       CO2MolFracStd=CO2MolFracStd, C1MolFracAvg=C1MolFracAvg, C1MolFracStd=C1MolFracStd,
                       C2MolFracAvg=C2MolFracAvg, C2MolFracStd=C2MolFracStd, C3MolFracAvg=C3MolFracAvg,
                       C3MolFracStd=C3MolFracStd, iC4MolFracAvg=iC4MolFracAvg, iC4MolFracStd=iC4MolFracStd,
                       nC4MolFracAvg=nC4MolFracAvg, nC4MolFracStd=nC4MolFracStd, iC5MolFracAvg=iC5MolFracAvg,
                       iC5MolFracStd=iC5MolFracStd, nC5MolFracAvg=nC5MolFracAvg, nC5MolFracStd=nC5MolFracStd,
                       C6MolFracAvg=C6MolFracAvg, C6MolFracStd=C6MolFracStd, KLambdaAvg=KLambdaAvg,
                       KLambdaStd=KLambdaStd, EtaAvg=EtaAvg, KEtaAvg=KEtaAvg, KEtaStd=KEtaStd)

    def addField(self, fieldName, fieldValue):
        if not fieldName in ControlledRelease.fields:
            raise KeyError(f'Field named {fieldName} must appear in Event Fields.')
        self.map[fieldName] = fieldValue
        self.__dict__[fieldName] = fieldValue

    def getField(self, fieldName):
        return self.map.get(fieldName)

    def getAllFields(self):
        return self.map

    def setExperimentInfo(self, eventID=None, ExperimentID=None, QCFlagCount=None, QCFlags=None,
                          tStart=None, tTransitioned=None, tSettled=None, tEnd=None,Duration=None, UTCStart=None,
                               UTCTransition=None, UTCSettled=None, UTCEnd=None,FlowmeterID=None, ActiveEPCount=None):
        self.addField('EventID', eventID)
        self.addField('ExperimentID', ExperimentID)
        self.addField('QCFlags', QCFlags)
        if QCFlagCount:
            self.addField("QCFlagCount", QCFlagCount)
        elif QCFlags:
            qcCount = len([i for i in QCFlags if i == '1'])
            self.addField("QCFlagCount", qcCount)
        else:
            self.addField("QCFlagCount", 0)
        self.addField('tStart', tStart)
        self.addField('tTransitioned', tTransitioned)
        self.addField('tSettled', tSettled)
        self.addField('tEnd', tEnd)
        if Duration:
            self.addField('Duration', Duration)
        else:
            self.addField('Duration', int(tEnd - tStart) if not (tEnd is None) and not (tStart is None) else None)
        if UTCStart:
            self.addField('UTCStart', UTCStart)
        else:
            self.addField('UTCStart',
                          tu.EpochtoDT(int(tStart)).strftime('%Y-%m-%d_%H:%M:%S.%f') if not tStart is None else None)
        if UTCTransition:
            self.addField('UTCTransition', UTCTransition)
        else:
            self.addField('UTCTransition', tu.EpochtoDT(int(tTransitioned)).strftime('%Y-%m-%d_%H:%M:%S.%f') if not tTransitioned is None else None)
        if UTCSettled:
            self.addField('UTCSettled', UTCSettled)
        else:
            self.addField('UTCSettled', tu.EpochtoDT(int(tSettled)).strftime('%Y-%m-%d_%H:%M:%S.%f') if not tSettled is None else None)
        if UTCEnd:
            self.addField('UTCEnd', UTCEnd)
        else:
            self.addField('UTCEnd', tu.EpochtoDT(int(tEnd)).strftime('%Y-%m-%d_%H:%M:%S.%f') if not tEnd is None else None)
        self.addField('FlowmeterID', FlowmeterID)
        self.addField('ActiveEPCount', ActiveEPCount)

    def setFlowInfo(self, FlowAvg=None, FlowStDev=None, FlowUncertainty=None, C1FlowAvg=None, C1FlowUncertainty=None,
                    BFE=None, BFU=None, BFT=None,
                    C2FlowAvg=None, C2FlowUncertainty=None, C3FlowAvg=None, C3FlowUncertainty=None, C4FlowAvg=None,
                    C4FlowUncertainty=None, THCFlowAvg=None, THCFlowUncertainty=None):
        self.addField('FlowAvg', FlowAvg)

        self.addField('FlowStDev', FlowStDev)
        self.addField('FlowUncertainty', FlowUncertainty)
        self.addField('BFE', BFE)
        self.addField('BFU', BFU)
        self.addField('BFT', BFT)

        self.addField('C1FlowAvg', C1FlowAvg)
        self.addField('C1FlowUncertainty', C1FlowUncertainty)
        self.addField('C2FlowAvg', C2FlowAvg)
        self.addField('C2FlowUncertainty', C2FlowUncertainty)
        self.addField('C3FlowAvg', C3FlowAvg)
        self.addField('C3FlowUncertainty', C3FlowUncertainty)
        self.addField('C4FlowAvg', C4FlowAvg)
        self.addField('C4FlowUncertainty', C4FlowUncertainty)
        self.addField('THCFlowAvg', THCFlowAvg)
        self.addField('THCFlowUncertainty', THCFlowUncertainty)

    def setEmissionPointInfo(self, OrificeControllerID=None, OrificeControllerPAvg=None,
                             OrificeControllerPStd=None, OrificeControllerTAvg=None, OrificeControllerTStd=None,
                             EPID=None, EPEquipmentGroup=None, EPEquipmentUnit=None, EPDescription=None,
                             EPLatitude=None, EPLongitude=None, EPAltitude=None, EPFlowLevel=None, EPFlowSetpoint=None,
                             EmissionIntent=None, EmissionCategory=None):

        self.addField('OrificeControllerID', OrificeControllerID)
        self.addField('OrificeControllerPAvg', OrificeControllerPAvg)
        self.addField('OrificeControllerPStd', OrificeControllerPStd)
        self.addField('OrificeControllerTAvg', OrificeControllerTAvg)
        self.addField('OrificeControllerTStd', OrificeControllerTStd)
        self.addField('EPID', EPID)
        self.addField('EPEquipmentGroup', EPEquipmentGroup)
        self.addField('EPEquipmentUnit', EPEquipmentUnit)
        self.addField('EPDescription', EPDescription)
        self.addField('EPLatitude', EPLatitude)
        self.addField('EPLongitude', EPLongitude)
        self.addField('EPAltitude', EPAltitude)
        self.addField('EPFlowLevel', EPFlowLevel)
        self.addField('EPFlowSetpoint', EPFlowSetpoint)
        self.addField('EmissionIntent', EmissionIntent)
        self.addField('EmissionCategory', EmissionCategory)

    def getEmissionPointInfo(self):
        fields = {}
        fields["OrificeControllerID"] = self.getField('OrificeControllerID')
        fields['OrificeControllerPAvg'] = self.getField('OrificeControllerPAvg')
        fields['OrificeControllerPStd'] = self.getField('OrificeControllerPStd')
        fields['OrificeControllerTAvg'] = self.getField('OrificeControllerTAvg')
        fields['OrificeControllerTStd'] = self.getField('OrificeControllerTStd')
        fields['EPID'] = self.getField('EPID')
        fields['EPEquipmentGroup'] = self.getField('EPEquipmentGroup')
        fields['EPEquipmentUnit'] = self.getField('EPEquipmentUnit')
        fields['EPDescription'] = self.getField('EPDescription')
        fields['EPLatitude'] = self.getField('EPLatitude')
        fields['EPLongitude'] = self.getField('EPLongitude')
        fields['EPAltitude'] = self.getField('EPAltitude')
        fields['EPFlowLevel'] = self.getField('EPFlowLevel')
        fields['EPFlowSetpoint'] = self.getField('EPFlowSetpoint')
        return fields

    def setRefInfo(self, RefEventID=None, RefFlowAvg=None, RefFlowUncertainty=None, RefPRatio=None, RefTRatio=None):
        self.addField('RefEventID', RefEventID)
        self.addField('RefFlowAvg', RefFlowAvg)
        self.addField('RefFlowUncertainty', RefFlowUncertainty)
        self.addField('RefPRatio', RefPRatio)
        self.addField('RefTRatio', RefTRatio)

    def setGCInfo(self, GCSampleCount=None, N2MolFracAvg=None, N2MolFracStd=None, CO2MolFracAvg=None, CO2MolFracStd=None,
                  C1MolFracAvg=None, C1MolFracStd=None, C2MolFracAvg=None, C2MolFracStd=None, C3MolFracAvg=None,
                  C3MolFracStd=None, iC4MolFracAvg=None, iC4MolFracStd=None, nC4MolFracAvg=None, nC4MolFracStd=None,
                  iC5MolFracAvg=None, iC5MolFracStd=None, nC5MolFracAvg=None, nC5MolFracStd=None, C6MolFracAvg=None,
                  C6MolFracStd=None, KLambdaAvg=None, KLambdaStd=None, EtaAvg=None, KEtaAvg=None, KEtaStd=None):

        self.addField('GCSampleCount', GCSampleCount)
        self.addField('N2MolFracAvg', N2MolFracAvg)
        self.addField('N2MolFracStd', N2MolFracStd)
        self.addField('CO2MolFracAvg', CO2MolFracAvg)
        self.addField('CO2MolFracStd', CO2MolFracStd)
        self.addField('C1MolFracAvg', C1MolFracAvg)
        self.addField('C1MolFracStd', C1MolFracStd)
        self.addField('C2MolFracAvg', C2MolFracAvg)
        self.addField('C2MolFracStd', C2MolFracStd)
        self.addField('C3MolFracAvg', C3MolFracAvg)
        self.addField('C3MolFracStd', C3MolFracStd)
        self.addField('iC4MolFracAvg', iC4MolFracAvg)
        self.addField('iC4MolFracStd', iC4MolFracStd)
        self.addField('nC4MolFracAvg', nC4MolFracAvg)
        self.addField('nC4MolFracStd', nC4MolFracStd)
        self.addField('iC5MolFracAvg', iC5MolFracAvg)
        self.addField('iC5MolFracStd', iC5MolFracStd)
        self.addField('nC5MolFracAvg', nC5MolFracAvg)
        self.addField('nC5MolFracStd', nC5MolFracStd)
        self.addField('C6MolFracAvg', C6MolFracAvg)
        self.addField('C6MolFracStd', C6MolFracStd)
        self.addField('KLambdaAvg', KLambdaAvg)
        self.addField('KLambdaStd', KLambdaStd)
        self.addField('EtaAvg', EtaAvg)
        self.addField('KEtaAvg', KEtaAvg)
        self.addField('KEtaStd', KEtaStd)