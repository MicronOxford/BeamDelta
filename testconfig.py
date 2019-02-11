#!/usr/bin/python
"""Config file for devicebase.

Import device classes, then define entries in DEVICES as:
   devices(CLASS, HOST, PORT, other_args)
"""
# Function to create record for each device.
from microscope.devices import device
# Import device modules/classes here.
#from microscope.cameras import andorsdk3
import microscope.testsuite.devices as testdevices

DEVICES = [
    device(testdevices.TestCamera, '127.0.0.1', 8000),
	device(testdevices.TestCamera, '127.0.0.1', 8001, com=6, baud=115200),
	device(testdevices.TestLaser, '127.0.0.1', 8002),
	device(testdevices.TestLaser, '127.0.0.1', 8003),
	device(testdevices.TestFilterWheel, '127.0.0.1', 8004),
	device(testdevices.DummyDSP, '127.0.0.1', 8005),
	device(testdevices.DummySLM, '127.0.0.1', 8006),
    device(testdevices.TestFilterWheel, '127.0.0.1', 8007),
#	device(andorsdk3.AndorSDK3, '127.0.0.1', 8002, uid='VSC-01344'),
]