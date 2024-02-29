import serial
import serial.tools.list_ports
import requests
import configparser
from AppIoT.models import DatiSeriale
from django.utils import timezone

class Bridge():

	def __init__(self):
		self.config = configparser.ConfigParser()
		#self.config.read('config.ini')
		#self.setupSerial()

	def setupSerial(self):
		# open serial port
		self.ser = None

		if not self.config.getboolean("Serial","UseDescription", fallback=False):
			self.portname = self.config.get("Serial","PortName", fallback="COM1")
		else:
			print("porte disponibili: ")
			ports = serial.tools.list_ports.comports()

			for port in ports:
				print (port.device)
				print (port.description)
				if self.config.get("Serial","PortDescription", fallback="arduino").lower() \
						in port.description.lower():
					self.portname = port.device

		try:
			if self.portname is not None:
				print ("connettendo a " + self.portname)
				self.ser = serial.Serial(self.portname, 9600, timeout=0)
		except:
			self.ser = None

		# self.ser.open()

		# buffer di input interno per la comunicazione seriale
		self.inbuffer = []

	def postdata(self, i, val):
		if i > 0:
			return
		url = self.config.get("HTTPAIO","Url") + "/data"
		myobj = {'value': val}
		headers = {'X-AIO-Key': self.config.get("HTTPAIO","X-AIO-Key") }
		print ("> Mando a " + url)

		x = requests.post(url, data=myobj, headers=headers)
		print(x.json())

	def loop(self):
		# loop infinito per il seriale
		#
		while (True):
			#mi aspetto il byte del seriale
			if not self.ser is None:

				if self.ser.in_waiting>0:
					# data available from the serial port
					lastchar=self.ser.read(1)

					if lastchar==b'\xfe': #EOL
						print("\nHo ricevuto il valore")
						self.useData()
						self.inbuffer =[]
					else:
						# append
						self.inbuffer.append (lastchar)

	def useData(self):
		# Ho ricevuto un intero pacchetto e devo usarlo
		if len(self.inbuffer)<3:   # almeno header, size, footer
			return False
		# split parts
		if self.inbuffer[0] != b'\xff':
			return False

		# se sono arrivato a questo punto ho un pacchetto corretto (inizia con ff e finisce con fe)
		numval = int.from_bytes(self.inbuffer[1], byteorder='little')

		for i in range (5): #numval
			#val = int.from_bytes(self.inbuffer[i+2], byteorder='little')
			val=100
			strval = "Sensore %d: %d " % (i, val)
			print(strval)
			DatiSeriale.objects.create(dati=strval) # Salva i dati nel modello DatiSeriale

	def useData1(self):
		for i in range (5): #numval
			#val = int.from_bytes(self.inbuffer[i+2], byteorder='little')
			val=111
			strval = "Sensore %d: %d " % (i, val)
			print(strval)
			DatiSeriale.objects.create(dati=strval)

if __name__ == '__main__':
	br=Bridge()
	br.loop()