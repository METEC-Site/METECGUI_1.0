import math
from copy import deepcopy

updatedConversionTable = {
    'temperature': {
        "F": {"abbr": "F", "units": "Fahrenheit",   "m": 1,       "b": 0},
        "C": {"abbr": "C", "units": "Celsius",      "m": (5 / 9), "b": -17.77777778},
        "K": {"abbr": "K", "units": "Kelvin",       "m": (5 / 9), "b": 255.37222222},
    },
    'pressure': {
        "PSIA":  {"abbr": "PSIA", "units": "PSI Absolute", "m": 1,          "b": 0},
        "PSIG":  {"abbr": "PSIG", "units": "PSI Gauge",    "m": 1,          "b": -14.7},
        "Torr":  {"abbr": "Torr", "units": "Torr",         "m": 51.714932,  "b": 0},
        "Bar":   {"abbr": "Bar",  "units": "Bar",          "m": .0689476,   "b": 0},
        "mBar":  {"abbr": "mBar", "units": "Milli-Bar",    "m": 68.9476,   "b": 0},
        "Atm":   {"abbr": "Atm",  "units": "Atmosphere",   "m": .06804595,    "b": 0},
        "kPa":   {"abbr": "kPa",  "units": "Kilopascal",   "m": 6.89476,    "b": 0}
    },
    'massflow': {
        'SLPM': {"abbr": "SLPM", "units": "Standard Liters Per Minute",   "m": 1,           "b": 0},
        'SCFH': {"abbr": "SCFH", "units": "Standard Cubic Feet Per Hour", "m": 2.118883,    "b": 0},

    },
    'voltage':{
        'V': {"abbr": "V", "units": "Voltage", "m": 1, "b": 0}
    },
    'speed':{
        'm/s': {"abbr": "m/s", "units": "Meters Per Second", "m": 1, "b": 0},
        'mph': {"abbr": "mph", "units": "miles per hour", "m": 2.236936, "b": 0}
    },
    'percent':{
        '%': {"abbr": "%",  "units": "Percent", "m": 1, "b": 0},
    },
    'time':{
        's': {'abbr': 's', 'units': 'Seconds', 'm': 1, 'b': 0},
        'min': {'abbr': 'min', 'units': 'Minutes', 'm': 1/60, 'b': 0},
        'hr': {'abbr': 'hr', 'units': 'Hours', 'm': 1/3600, 'b': 0},
        'days': {'abbr': 'days', 'units': 'Days', 'm': 1/86400, 'b': 0},
    }
}

absoluteMinimums = {
    'temperature': {
        'F': -459.67,
        'C': -273.15,
        'K': 0
    },
    'pressure': {
        "PSIA":  0,
        "PSIG": -14.7,
        "Torr":  0,
        "Bar":   0,
        "Atm":   0,
        "kPa":   0,
    }
}

def windCardinalToRadial(u,v,w):
    magnitude = math.sqrt(u**2 + v**2 + w**2)
    radialDirection = u/v

def getDict(baseUnit):
    for unitType, conversionDict in updatedConversionTable.items():
        if baseUnit == unitType:
            return deepcopy([unitType, conversionDict])
        for unitName, unitData in conversionDict.items():
            if baseUnit in unitData.values():
                return deepcopy([unitType, conversionDict])
    return [None, {}]

def convert(value, fromUnit, toUnit):
    # TODO: Check this method. Was prone to breaking.
    if fromUnit is toUnit:
        return value
    if fromUnit in [None, 'units'] or toUnit in [None, 'units']:
        return value
    fromData = toData = None

    for tableName, table in updatedConversionTable.items():
        for rowName, singleRow in table.items():
            if fromUnit == rowName or fromUnit in singleRow.values():
                fromData = singleRow
            if toUnit == rowName or toUnit in singleRow.values():
                toData = singleRow
        if (fromData and not toData) or (toData and not fromData):
            #raise error? This indicates they are not the same units, or that the unit doesn't exist in the table.
            raise ValueError(f'Cannot convert from units {fromUnit} to {toUnit}; They are not the same type of unit or '
                          f'one or both is not registered in the conversion table.')
    if not fromData or not toData:
        raise ValueError(f'Cannot convert from units {fromUnit} to {toUnit}; Possibly cannot find unit in Conversions')


    valType = type(value)
    toNormalM = fromData['m']
    toNormalB = fromData['b']

    toConvertedM = toData['m']
    toConvertedB = toData['b']

    toNormalValue = (value - toNormalB) / toNormalM
    toConvertedValue = toNormalValue * toConvertedM + toConvertedB

    # Type match incoming and outgoing value.
    if valType is int:
        toConvertedValue = round(toConvertedValue)
    return valType(toConvertedValue)


def getAbsoluteMin(unit):
    min = list(filter(lambda x: unit in x.keys(), absoluteMinimums.values()))
    if not min:
        return None
    return min[0][unit]

def getUnitType(unit):
    for key, values in updatedConversionTable.items():
        abbrs = []
        for v in values.values():
            abbrs.append(v["abbr"])
        if unit in abbrs:
            return key

def uvToDegMag(u, v):
    angle = math.degrees(math.atan2(u, v))+90
    if angle < 0:
        angle+=360
    mag = math.sqrt(u**2 + v**2)
    return angle, mag

def uvFromDegMag(deg, mag):
    u = -mag * math.sin(math.radians(90+deg))
    v = -mag * math.cos(math.radians(90+deg))
    return u, v