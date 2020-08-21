from ustruct import pack, unpack
import utime

TEMP_PRESS_DIG_REG = 0x88
HUM_DIG_REG = 0xA1
HUM_DIG_REG2 = 0xE1

CONFIG_REG = 0xF5
CTRL_MEAS_REG = 0xF4
STATUS_REG = 0xF3
CTRL_HUM_REG = 0xF2
RESET_REG = 0xE0
ID_REG = 0xD0

TEMP_MSB = 0xFA
PRESS_MSB = 0xF7
HUM_MSB = 0xFD

MODE_SLEEP = 0x00
MODE_FORCED = 0x01
MODE_NORMAL = 0x03

class BME280:
  def __init__(self, addr=None, i2c=None):
    if i2c is None:
      raise TypeError('I2C object required for constructor!')
    self.i2c = i2c

    if addr is None:
      raise TypeError('Address of BME280 required for constructor!')
    self.addr = addr
   
    # Read constants, little-endian 
    TP = self.i2c.readfrom_mem(self.addr, TEMP_PRESS_DIG_REG, 24)
    self.dig_T1, self.dig_T2, self.dig_T3, \
    self.dig_P1, self.dig_P2, self.dig_P3, self.dig_P4, \
    self.dig_P5, self.dig_P6, self.dig_P7, self.dig_P8, \
    self.dig_P9 = unpack('<HhhH8h', TP)

    H1 = self.i2c.readfrom_mem(self.addr, HUM_DIG_REG, 1)
    self.dig_H1 = unpack('<B', H1)[0]

    H = self.i2c.readfrom_mem(self.addr, HUM_DIG_REG2, 7)
    self.dig_H2, self.dig_H3, self.dig_H4, self.dig_H5, \
    self.dig_H6 = unpack('<hBbhb', H)
    # H4 is actually contents of (0xE4 << 4) | (0xE5 & 0xF)
    self.dig_H4 = (self.dig_H4 << 4) | (self.dig_H5 & 0xF) 
    # H5's LSB is only bits [7:4] of 0xE5, so shift off bits [3:0]
    self.dig_H5 = self.dig_H5 >> 4

    # print('\n\n\n')
    # print('Temperature: {:d} {:d} {:d}'.format(self.dig_T1, self.dig_T2, self.dig_T3))
    # print('Pressure: {:d} {:d} {:d} {:d} {:d} {:d} {:d} {:d} {:d}'.format(self.dig_P1, self.dig_P2, \
    # self.dig_P3, self.dig_P4, self.dig_P5, self.dig_P6, self.dig_P7, self.dig_P8, self.dig_P9))
    # print('Humidity: {:d} {:d} {:d} {:d} {:d} {:d}'.format(self.dig_H1, self.dig_H2, self.dig_H3, \
    # self.dig_H4, self.dig_H5, self.dig_H6))

    # Set sensible defaults
    self.set_config(0x60, 0x10)
    standby, filter_coefficient = self.read_config() 
    # print('Standby: {:X}, Filter: {:X}'.format(standby, filter_coefficient))

    self.set_ctrl_hum(0x04)
    self.set_ctrl_meas(0x20, 0x0C, 0x01)
    ctrl_hum = self.read_ctrl_hum()
    # print('osrs_h: {:X}'.format(ctrl_hum))
    osrs_p, osrs_t, mode = self.read_ctrl_meas()
    # print('osrs_p: {:X}, osrs_t: {:X}, mode: {:X}'.format(osrs_p, osrs_t, mode))

  def read_data(self):
    # Wake from sleep mode first
    osrs_p, osrs_t, mode = self.read_ctrl_meas()
    # Only set to forced mode if read mode is sleep
    if mode == MODE_SLEEP:
      self.set_ctrl_meas(osrs_p, osrs_t, MODE_FORCED)

    # Wait until measurement is transferred to data registers
    while self.i2c.readfrom_mem(self.addr, STATUS_REG, 1)[0] & 0x08:
      utime.sleep_ms(2)
    
    # Read temperature, then pressure and humidity
    rx_temp = self.i2c.readfrom_mem(self.addr, TEMP_MSB, 3)
    rx_temp = (rx_temp[0] << 16 | rx_temp[1] << 8 | rx_temp[2]) >> 4
    self.t_fine = 0
    temperature = self.compensate_temperature(rx_temp)

    rx_pres = self.i2c.readfrom_mem(self.addr, PRESS_MSB, 3)
    rx_pres = (rx_pres[0] << 16 | rx_pres[1] << 8 | rx_pres[2]) >> 4
    pressure = self.compensate_pressure(rx_pres)

    rx_hum = self.i2c.readfrom_mem(self.addr, HUM_MSB, 2)
    rx_hum = (rx_hum[0] << 8 | rx_hum[1]) & 0xFFFF
    humidity = self.compensate_humidity(rx_hum)

    return pressure, temperature, humidity

  def read_config(self):
    config = self.i2c.readfrom_mem(self.addr, CONFIG_REG, 1)[0]
    # Output is in order standby, filter coefficient
    return config & 0xE0, config & 0x1C

  def read_ctrl_hum(self):
    ctrl_hum = self.i2c.readfrom_mem(self.addr, CTRL_HUM_REG, 1)[0]
    return ctrl_hum

  def read_ctrl_meas(self):
    ctrl_meas = self.i2c.readfrom_mem(self.addr, CTRL_MEAS_REG, 1)[0]
    # Output is in order P, T, Mode
    return ctrl_meas & 0x1C, ctrl_meas & 0xE0, ctrl_meas & 0x03

  def set_config(self, standby, filter_coefficient):
    config = (standby | filter_coefficient) & 0xFE
    config = pack('<b', config)
    self.i2c.writeto_mem(self.addr, CONFIG_REG, config)

  def set_ctrl_hum(self, osrs_h):
    ctrl_hum = pack('<b', osrs_h)
    self.i2c.writeto_mem(self.addr, CTRL_HUM_REG, ctrl_hum)

  def set_ctrl_meas(self, osrs_p, osrs_t, mode):
    ctrl_meas_tx = (osrs_p | osrs_t | mode)
    ctrl_meas_tx = pack('<b', ctrl_meas_tx)
    self.i2c.writeto_mem(self.addr, CTRL_MEAS_REG, ctrl_meas_tx)

  def compensate_pressure(self, p):
    var1 = float(self.t_fine) / 2.0 - 64000
    var2 = var1 * var1 * float(self.dig_P6) / 32768
    var2 = var2 + var1 * float(self.dig_P5) * 2.0
    var2 = var2 / 4 + float(self.dig_P4) * 65536
    var1 = (float(self.dig_P3) * var1 * var1 / 524288 + float(self.dig_P2) * var1) / 524288.0
    var1 = (1.0 + var1 / 32768) * float(self.dig_P1)

    if not var1:
      return 0

    pres = 1048576 - p
    pres = (pres - (var2 / 4096)) * 6250 / var1
    var1 = self.dig_P9 * pres * pres / 2147483649
    var2 = pres * (self.dig_P8) / 32768
    pres = pres + (var1 + var2 + (self.dig_P7)) / 16
    
    return pres

  def compensate_temperature(self, t):
    var1 = (float(t) / 16384 - float(self.dig_T1) / 1024) * float(self.dig_T2)
    var2 = (float(t) / 131072 - float(self.dig_T1) / 8192) \
      * (float(t) / 131072 - float(self.dig_T1) / 8192) \
      * float(self.dig_T3)
    self.t_fine = int(var1 + var2)

    return (var1 + var2) / 5120.0

  def compensate_humidity(self, h):
    var = float(self.t_fine) - 76800
    var = (h - (float(self.dig_H4) * 64 + float(self.dig_H5) / 16384 * var)) \
      * (float(self.dig_H2) / 65536 * (1 + float(self.dig_H6) / 67108864 * var \
      * (1 + float(self.dig_H3) / 67108864 * var)))
    var = var * (1 - float(self.dig_H1) * var / 524288)

    if var > 100:
      var = 100
    elif var < 0:
      var = 0

    return var

