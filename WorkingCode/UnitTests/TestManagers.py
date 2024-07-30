# import os
# import tempfile
# import unittest
# import threading
# import time
# import logging
#
#
# from Framework.BaseClasses.Events import EventTypes, EventPayload, Destination, Package, ChannelType
# from Framework.BaseClasses.Subscriber import Subscriber
# from Framework.BaseClasses.Worker import Worker
# from Framework.BaseClasses.Destination import Destination
# from Framework.Manager.EventManager import EventManager
# from Framework.Manager.CommandManager import CommandManager
# from Framework.Archive.DirectoryArchiver import DirectoryArchiver
# from Framework.Manager.ObjectManager import ObjectManager
# from UnitTests import TestAll as TA
#
#
# class testWorker(Subscriber, Worker):
#     def __init__(self, commandManager=None, dataManager=None, eventManager=None, name=None, subscriptions=None):
#         Worker.__init__(self, commandManager=commandManager, dataManager=dataManager, eventManager=eventManager, name=name)
#         Subscriber.__init__(self, name, eventManager, subscriptions=subscriptions)
#
# class testRecipient(Subscriber, Worker, Destination):
#     def __init__(self, commandManager=None, dataManager=None, eventManager=None, name=None, subscriptions=None):
#         Worker.__init__(self, commandManager=commandManager, dataManager=dataManager,
#                         eventManager=eventManager, name=name)
#         Subscriber.__init__(self, name, eventManager, subscriptions)
#
#
# class TestDirectoryArchiver(unittest.TestCase):
#     @TA.CleanNamespace('test_shutdown')
#     def test_shutdown(self):
#         with tempfile.TemporaryDirectory() as tDir:
#             with DirectoryArchiver(name="unittestArchiver", baseDir=tDir, template="tmp1_%Y%m%d", configFiles=[]) as da1:
#                 cm = CommandManager(da1, 'commandManager')
#                 em = EventManager(da1, 'eventManager')
