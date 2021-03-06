#!/usr/bin/env python

# Third party library; "pip install requests" if getting import errors.
import requests

# We use raw sockets.
import socket

# We unpack structures.
import struct

# We use namedtuple to reduce index errors.
import collections

# We use binascii to convert some consts from hex.
import binascii

# We use Python enums.
import enum

class OperateMode(enum.Enum):
 POWER_OFF = 1
 POWER_ON = 2
 GOOUT_OFF = 3
 GOOUT_ON = 4
 INSIDE_HEAT = 5
 ONDOL_HEAT = 6
 REPEAT_RESERVE = 7
 CIRCLE_RESERVE = 8
 SIMPLE_RESERVE = 9
 HOTWATER_ON = 10
 HOTWATER_OFF = 11
 WATER_SET_TEMP = 12
 QUICK_HOTWATER = 13
 HEAT_LEVEL = 14
 ACTIVE = 128

class ModeState(enum.Enum):
 POWER_OFF = 1
 GOOUT_ON = 2
 INSIDE_HEAT = 3
 ONDOL_HEAT = 4
 SIMPLE_RESERVE = 5
 CIRCLE_RESERVE = 6
 HOTWATER_ON = 8

class HeatLevel(enum.Enum):
 LOW = 1
 MEDIUM = 2
 HIGH = 3

class TempControlType(enum.IntFlag):

 # 3rd bit.
 POINTINSIDE = 32

 # 4th bit.
 POINTONDOL = 16
 
 # 5th bit.
 POINTWATER = 8
 
 # 6th - 8th bits (last 3 bits).
 WATERMODE = 7

class NavienSmartControl:

 # This prevents the requests module from creating its own user-agent.
 stealthyHeaders = {'User-Agent': None }

 # The Navien server.
 navienServer = 'ukst.naviensmartcontrol.com'
 navienWebServer = 'https://' + navienServer
 navienServerSocketPort = 6001
 
 def __init__(self, userID, passwd):
  self.userID = userID
  self.passwd = passwd
  self.connection = None

 def login(self):
  # Login.
  response = requests.post(NavienSmartControl.navienWebServer + '/mobile_login_check.asp', headers=NavienSmartControl.stealthyHeaders, data={'UserID': self.userID, 'Passwd': self.passwd, 'BundleVersion': '8', 'AutoLogin': '1', 'smartphoneID': '2'})

  # If an error occurs this will raise it, otherwise it returns the encodedUserID (this is just the BASE64 UserID typically).
  return self.handleResponse(response)

 # This is the list of the details for the boiler controller or "gateway". Note how no login state is required.
 def gatewayList(self, encodedUserID):
  # Get the list of connected devices.
  response = requests.post(NavienSmartControl.navienWebServer + '/mobile_gateway_list.asp', headers=NavienSmartControl.stealthyHeaders, data={'UserID': encodedUserID, 'Ticket':'0'})

  # The server replies with a pipe separated response.
  return self.handleResponse(response)

 def handleResponse(self, response):

  # The server replies with a pipe separated response.
  response_status = response.text.split('|')

  # The first value is either a status code or sometimes a raw result.
  response_status_code = response_status[0]

  if response_status_code == '0':
   raise Exception('Error: Controller not connected to the Internet server; please check your Wi-Fi network and wait until the connection to the Internet server is restored automatically.')
  elif response_status_code == '1':
   raise Exception('Error: Login details incorrect. Please note, these are case-sensitive.')
  elif response_status_code == '2':
   raise Exception('Error: The ID you have chosen is already in use.')
  elif response_status_code == '3':
   return response_status[1]
  elif response_status_code == '4':
   raise Exception('Error: Invalid ID.')
  elif response_status_code == '9':
   raise Exception('Error: The Navien TOK account you have chosen is already in use by other users. Try again later.')
  elif response_status_code == '201':
   raise Exception('Error: The software is updated automatically and a continuous internet connection is required for this. If the router is not on continually, updates may be missed.')
  elif response_status_code == '202':
   if len(response_status) == 2:
    raise Exception('Error: Service inspection. Please wait until the inspection is done and try again. (Inspection hour:' + response_status[1] + ')')
   else:
    raise Exception('Error: Service inspection. Please wait until the inspection is done and try again.')
  elif response_status_code == '203':
   raise Exception('Error: Shutting down the service. Thank you for using this service. Closing the current program.')
  elif response_status_code == '210':
   raise Exception('Error: This version is too old.')
  elif response_status_code == '999':
   raise Exception('Error: Sorry. Please try again later.')
  else:
   return response_status
 
 def connect(self, controllerMACAddress):

  # Construct a socket object.
  self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

  # Connect to the socket server.
  self.connection.connect((NavienSmartControl.navienServer, NavienSmartControl.navienServerSocketPort))

  # Request the boiler status.
  self.connection.sendall((self.userID + '$' + 'iPhone1.0' + '$' + controllerMACAddress + '\n').encode())

  # Receive the boiler status.
  data = self.connection.recv(1024)

  # Return the parsed home state data.
  return self.parseHomeState(data)

 def parseHomeState(self, data):

  # The data is returned with a fixed header for the first 42 bytes.
  homeStateColumns = collections.namedtuple('homeState', ['deviceid','nationCode','hwRev','swRev','netType','controlType','boilerModelType','roomCnt','smsFg','errorCode','hotWaterSetTemp','heatLevel','optionUseFg','currentMode','currentInsideTemp','insideHeatTemp','ondolHeatTemp','repeatReserveHour','repeatReserveMinute','hour24ReserveTime1','hour24ReserveTime2','hour24ReserveTime3','simpleReserveSetTime','simpleReserveSetMinute','operateMode','tempControlType','hotwaterMin','hotwaterMax','ondolHeatMin','ondolHeatMax','insideHeatMin','insideHeatMax','reserve09', 'reserve10'])
  homeState = homeStateColumns._make(struct.unpack('          8s          B          B       B        B          B               B              B        B         H              B             B            B            B                B                  B               B                B                     B                     B                    B                           B             B                          B                B              B               B             B               B              B               B               B             B            B', data[:42]))

  # If the roomCnt > 1 then the remaining data will be room state information.
  if len(data) > 42:
   print('Warning : Extra roomState data found but not implemented in this version.')
 
  # These are hardcoded values to watch out for.
  if data == binascii.unhexlify('444444444400000000000000000000') or data == binascii.unhexlify('04040404040404040404'):
   raise Exception('An error occurred in the process of retrieving data; please restart to retry.')

  # Return the resulting parsed data.
  return homeState

 def printHomeState(self, homeState):
  print('Device ID: ' + ':'.join('%02x' % b for b in homeState.deviceid))
  print('Country Code: ' + str(homeState.nationCode))
  print('Hardware Revision: V' + str(homeState.hwRev))
  print('Software Version: V' + str(homeState.swRev) + '.0')
  print('Network Type: ' + str(homeState.netType))
  print('Control Type?: ' + str(homeState.controlType))
  print('Boiler Model Type: ' + str(homeState.boilerModelType))
  print('Room Controllers: ' + str(homeState.roomCnt))
  print('smsFg?: ' + str(homeState.smsFg))
  print('Error: ' + ('No Error' if homeState.errorCode == 0 else homeState.errorCode))
  print('Hot Water Set Temperature: ' + str(self.getTemperatureFromByte(homeState.hotWaterSetTemp)) + ' °C')
  print('Heat Intensity Type: ' + [ 'Unknown', 'Low', 'Medium', 'High' ][homeState.heatLevel])
  print('Option Use Flags: ' + bin(homeState.optionUseFg) + (' (Usable 24 Hour Reserve)' if homeState.optionUseFg & 128 == 128 else ''))
  print()

  print('Current Mode: ', end = '')
  if homeState.currentMode == ModeState.POWER_OFF.value:
   print('Powered Off')
  elif homeState.currentMode == ModeState.GOOUT_ON.value:
   print('Holiday Mode')
  elif homeState.currentMode == ModeState.INSIDE_HEAT.value:
   print('Room Temperature Control')
  elif homeState.currentMode == ModeState.ONDOL_HEAT.value:
   print('Central Heating Control')
  elif homeState.currentMode == ModeState.SIMPLE_RESERVE.value:
   print('Heating Inteval')
  elif homeState.currentMode == ModeState.CIRCLE_RESERVE.value:
   print('24 Hour Program')
  elif homeState.currentMode == ModeState.HOTWATER_ON.value:
   print('Hot Water Only')
  else:
   print(str(homeState.currentMode))

  print('Current Room Temperature: ' + str(self.getTemperatureFromByte(homeState.currentInsideTemp)) + ' °C')
  print('Inside Heating Temperature: ' + str(self.getTemperatureFromByte(homeState.insideHeatTemp)) + ' °C')
  print('Central Heating Temperature: ' + str(self.getTemperatureFromByte(homeState.ondolHeatTemp)) + ' °C')
  print()
  print('Heating Timer Interval: Every ' + str(homeState.repeatReserveHour) + ' hour(s)')
  print('Heating Timer Duration: ' + str(homeState.repeatReserveMinute) + ' minute(s)')
  print()
  print('24Hour Schedule (00-08h): ' + bin(homeState.hour24ReserveTime1))
  print('24Hour Schedule (09-16h): ' + bin(homeState.hour24ReserveTime2))
  print('24Hour Schedule (17-24h): ' + bin(homeState.hour24ReserveTime3))
  print()
  print('Simple Reserve Set Time: ' + str(homeState.simpleReserveSetTime))
  print('Simple Reserve Set Minute: ' + str(homeState.simpleReserveSetMinute))
  print()
  print('Operation Mode Flags: ' + bin(homeState.operateMode) + (' (Active)' if homeState.operateMode & OperateMode.ACTIVE.value else ''))
  print()
  print('Temperature Control Supported Types: ' + bin(homeState.tempControlType))
  if homeState.tempControlType & TempControlType.POINTINSIDE: print(' (POINTINSIDE)')
  if homeState.tempControlType & TempControlType.POINTONDOL: print(' (POINTONDOL)')
  if homeState.tempControlType & TempControlType.POINTWATER: print(' (POINTWATER)')
  if homeState.tempControlType & TempControlType.WATERMODE.value > 0: print(' (WATERMODE_' + str(homeState.tempControlType & TempControlType.WATERMODE.value) + ') = ' + ['Unknown','Stepped','Temperature'][(homeState.tempControlType & TempControlType.WATERMODE.value)-1] + ' Controlled')
  print()

  print('Hot Water Temperature Supported Range: ' + str(self.getTemperatureFromByte(homeState.hotwaterMin)) + ' °C - ' + str(self.getTemperatureFromByte(homeState.hotwaterMax)) + ' °C')
  print('Central Heating Temperature Supported Range: ' + str(self.getTemperatureFromByte(homeState.ondolHeatMin)) + ' °C - ' + str(self.getTemperatureFromByte(homeState.ondolHeatMax)) + ' °C')
  print('Room Temperature Supported Range: ' + str(self.getTemperatureFromByte(homeState.insideHeatMin)) + ' °C - ' + str(self.getTemperatureFromByte(homeState.insideHeatMax)) + ' °C')
  print()
  print('Reserved 09: ' + str(homeState.reserve09))
  print('Reserved 10: ' + str(homeState.reserve10))

 def getTemperatureByte(self, temperature):
  return int(2.0 * temperature)

 def getTemperatureFromByte(self, temperatureByte):
  return float((temperatureByte >> 1) + (0.5 if temperatureByte & 1 else 0))

 def setOperationMode(self, homeState, operateMode, value01, value02, value03, value04, value05):

  commandListSequence = 0
  commandListCommand = 131
  commandListDataLength = 21
  commandListCount = 0

  sendData = bytearray([commandListSequence, commandListCommand, commandListDataLength, commandListCount])
  sendData.extend(homeState.deviceid)

  commandSequence = 1
  sendData.extend([commandSequence, operateMode.value, value01, value02, value03, value04, value05]);

  self.connection.sendall(sendData)

 # ------ Set OperationMode convenience methods --------- #

 def setPowerOff(self, homeState):
  return self.setOperationMode(homeState, OperateMode.POWER_OFF, 1, 0, 0, 0, 0)

 def setPowerOn(self, homeState):
  return self.setOperationMode(homeState, OperateMode.POWER_ON, 1, 0, 0, 0, 0)

 def setGoOutOff(self, homeState):
  return self.setOperationMode(homeState, OperateMode.GOOUT_OFF, 1, 0, 0, 0, 0)

 def setGoOutOn(self, homeState):
  return self.setOperationMode(homeState, OperateMode.GOOUT_ON, 1, 0, 0, 0, 0)

 def setInsideHeat(self, homeState, temperature):
  if (temperature < self.getTemperatureFromByte(homeState.insideHeatMin) or temperature > self.getTemperatureFromByte(homeState.insideHeatMax)): raise ValueError('Temperature specified is outside the boiler\'s supported range.')
  return self.setOperationMode(homeState, OperateMode.INSIDE_HEAT, 1, 0, 0, 0, self.getTemperatureByte(temperature))

 def setOndolHeat(self, homeState, temperature):
  if (temperature < self.getTemperatureFromByte(homeState.ondolHeatMin) or temperature > self.getTemperatureFromByte(homeState.ondolHeatMax)): raise ValueError('Temperature specified is outside the boiler\'s supported range.')
  return self.setOperationMode(homeState, OperateMode.ONDOL_HEAT, 1, 0, 0, 0, self.getTemperatureByte(temperature))

 def setRepeatReserve(self, homeState, hourInterval, durationMinutes):
  return self.setOperationMode(homeState, OperateMode.REPEAT_RESERVE, 1, 0, 0, hourInterval, durationMinutes)

 def setCircleReserve(self, homeState, schedule1, schedule2, schedule3):
  return self.setOperationMode(homeState, OperateMode.CIRCLE_RESERVE, 1, 0, schedule1, schedule2, schedule3)

 def setHotWaterOn(self, homeState):
  return self.setOperationMode(homeState, OperateMode.HOTWATER_ON, 1, 0, 0, 0, 0)

 def setHotWaterOff(self, homeState):
  return self.setOperationMode(homeState, OperateMode.HOTWATER_OFF, 1, 0, 0, 0, 0)

 def setHotWaterHeat(self, homeState, temperature):
  if (temperature < self.getTemperatureFromByte(homeState.hotwaterMin) or temperature > self.getTemperatureFromByte(homeState.hotwaterMax)): raise ValueError('Temperature specified is outside the boiler\'s supported range.')
  return self.setOperationMode(homeState, OperateMode.WATER_SET_TEMP, 1, 0, 0, 0, self.getTemperatureByte(temperature))

 def setQuickHotWater(self, homeState):
  return self.setOperationMode(homeState, OperateMode.QUICK_HOTWATER, 1, 0, 0, 0, 0)

 def setHeatLevel(self, homeState, heatLevel):
  return self.setOperationMode(homeState, OperateMode.HEAT_LEVEL, 1, 0, 0, 0, heatLevel.value)