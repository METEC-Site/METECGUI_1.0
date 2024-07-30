from enum import Enum

# todo: incorporate these QC's into the event generations.
class QC_FLAGS(Enum):
    MISSING_REF    = 0 # no reference event available.
    PARTIAL_EXP    = 1 # Experiment exists but only partially covers this emission.
    METER_SPAN_MAX = 2 # Metered flow is above 90% of full span.
    METER_SPAN_MIN = 3 # Metered flow is below 10% of full span.
    METER_FLOW_DFT = 4 # Metered flow drifts over the course of the event by 10% or more.
    CTRLR_PRES_DEV = 5 # Absolute pressure at controller drifts by 10% of cal period.
    CTRLR_TEMP_DEV = 6 # Absolute temperature at controller drifts by 10% of cal period.
    SETTLED_MISSING= 7 # tSettled not identified. Reported equal to tTransitioned.

def getBaseQC():
    # returns the default binary qc representation. The number of 0's after the 0b should be the same as the number of
    # flags in QC_FLAGS
    base = 0b00000000
    strBase = "{0:b}".format(base)
    return strBase

def addQCFlag(flag, event):
    currentFlagsStr = event.getField('QCFlags')
    currentFlagsBin = int(currentFlagsStr,2)
    shift = 0b1 << flag.value
    updatedFlagsStr = currentFlagsBin | shift
    updatedFlagsBin = "{0:b}".format(updatedFlagsStr)
    event.addField('QCFlags', updatedFlagsBin)

def toDigit(stateStr):
    state = 0
    currDigits = 0
    for singleBin in stateStr:
        stateRep = 1-int(singleBin)
        state += 2**currDigits * stateRep
        currDigits += 1
    return state