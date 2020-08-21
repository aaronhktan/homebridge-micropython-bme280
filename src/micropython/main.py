from machine import I2C, Pin
import utime
from umqtt.robust import MQTTClient

import bme280
import ssd1306

# I2C port for BME
i2c_1 = I2C(-1, Pin(2), Pin(0))
bme = bme280.BME280(0x76, i2c_1)

# I2C port for OLED
i2c_2 = I2C(-1, Pin(5), Pin(4))
oled = ssd1306.SSD1306_I2C(64, 48, i2c_2)

# MQTT
c = MQTTClient('<client name here>', '192.168.0.38')
c.DEBUG = True
c.connect()

while True:
  pressure, temperature, humidity = bme.read_data()

  oled.fill(0)
  oled.text(str(round(temperature, 2)) + 'C', 0, 0)  
  oled.text(str(round(humidity, 2)) + '%', 0, 10)
  oled.text(str(round(pressure / 100, 1)) + 'hPa', 0, 20)
  oled.show()

  c.publish('MicroPython_BME280/pressure', str(pressure))
  c.publish('MicroPython_BME280/temperature', str(temperature))
  c.publish('MicroPython_BME280/humidity', str(humidity)) 

  utime.sleep(30)

