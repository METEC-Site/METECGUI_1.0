import datetime as dt
import unittest

import Utils.ClassUtils as cu
import Utils.TimeUtils as tu
import pytz
from Framework.BaseClasses.Commands import CommandClass
from Framework.BaseClasses.Readers.IntervalReader import IntervalReader
from Framework.BaseClasses.Readers.Reader import Reader
from Framework.BaseClasses.Uncertainty import Uncertainty
from UnitTests import TestAll as TA


class ReaderChild1(Reader, CommandClass):
    pass

class ReaderChild2(ReaderChild1):
    pass

class TestClassUtils(unittest.TestCase):
    c1 = ReaderChild1

    @TA.CleanNamespace('test_isCommandClass')
    def test_isCommandClass(self):
        self.assertEqual(cu.isCommandClass(TestClassUtils.c1), True)

    @TA.CleanNamespace('test_isReaderClass')
    def test_isReaderClass(self):
        self.assertEqual(cu.isReaderClass(ReaderChild1), True)
        self.assertEqual(cu.isReaderClass(ReaderChild2), True)
        ir1 = IntervalReader('IR1', None)
        self.assertEqual(cu.isReader(ir1), True)

    @TA.CleanNamespace('test_isUncertainty')
    def test_isUncertainty(self):
        unc1 = Uncertainty(10, 1)
        self.assertEqual(cu.isUncertainty(unc1), True)

    @TA.CleanNamespace('test_isPayload')
    def test_isPayload(self):
        import Framework.BaseClasses.Package as Pkg
        pl = Pkg.Payload('Somewhere')
        self.assertEqual(cu.isPayload(pl), True)

        import Framework.BaseClasses.Events as ev
        evPl = ev.EventPayload()
        self.assertEqual(cu.isPayload(evPl), True)


class TestTimeUtils(unittest.TestCase):
    @TA.CleanNamespace('testEpochDTConvert')
    def testEpochDTConvert(self):
        bdayEpoch = 792547200
        utc = pytz.UTC
        bdayDT = dt.datetime(year=1995, month=2, day=12, hour=0, minute=0, second=0, tzinfo=utc)
        convToEpoch = tu.DTtoEpoch(bdayDT)
        convToDT = tu.EpochtoDT(bdayEpoch)
        self.assertEqual(convToEpoch, bdayEpoch)
        self.assertEqual(bdayDT, convToDT)

    @TA.CleanNamespace('testNow')
    def testNow(self):
        now1 = tu.nowDT()
        now2a = tu.nowEpoch()
        now2 = tu.EpochtoDT(now2a)
        self.assertAlmostEqual(tu.DTtoEpoch(now1), tu.DTtoEpoch(now2))

    @TA.CleanNamespace('testEpochDTConvertTZ')
    def testEpochDTConvertTZ(self):
        tzStr = 'US/Mountain'
        bogusTZ = 'US/FooBar'
        tz = pytz.timezone(tzStr)
        nowEpoch = tu.nowEpoch()
        nowConvDT = tu.EpochtoDT(nowEpoch)
        nowConvDTmtnStr = tu.EpochtoDT(nowEpoch, tzStr)
        nowConvDTmtnTz = tu.EpochtoDT(nowEpoch, tz)
        nowBogus = tu.EpochtoDT(nowEpoch, bogusTZ)

        nowConvDTtoEpoch = tu.DTtoEpoch(nowConvDT)
        nowConvDTmtnStrToEpoch = tu.DTtoEpoch(nowConvDTmtnStr)
        nowConvDTmtnTzToEpoch = tu.DTtoEpoch(nowConvDTmtnTz)
        nowBogusToEpoch = tu.DTtoEpoch(nowBogus)
        unique = {nowEpoch, nowConvDTmtnTzToEpoch, nowConvDTmtnStrToEpoch, nowConvDTtoEpoch, nowBogusToEpoch}
        self.assertEqual(len(unique), 1)

    @TA.CleanNamespace('testDisplayTime')
    def testDisplayTime(self):
        time1 = dt.datetime(year=2019, month=5, day=4, hour=12, minute=34, second=56, tzinfo=pytz.timezone('UTC'))
        dispT1 = tu.displayLocal(time1) # Since time1 is naive, it is presumed to be local system timezone.
        manualT1 = time1.strftime(tu.formats[tu.FormatKeys.FileSafe])
        self.assertEqual(dispT1, manualT1)

        denTZ = pytz.timezone('US/Mountain')

        timeDen = dt.datetime(year=2019, month=5, day=4, hour=12, minute=34, second=56, tzinfo=denTZ)
        dispT2utc = tu.displayLocal(timeDen, 'UTC')
        manualT2utc = tu.EpochtoDT(tu.DTtoEpoch(timeDen)).strftime(tu.formats[tu.FormatKeys.FileSafe])
        self.assertEqual(manualT2utc, dispT2utc, msg=f'manual time: {manualT2utc} \ndisplay time: {dispT2utc}')

        dispDen = tu.displayLocal(timeDen)
        self.assertEqual(manualT1, dispDen)


