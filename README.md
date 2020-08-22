# Homebridge Plugin for BME280 connected to a WeMos D1 Mini

This is a Homebridge plugin for BME280 temperature, humidity, and barometric pressure sensor, connected to a WeMos D1 or other ESP8266 board, sending data over MQTT to the Raspberry Pi 3.

<img src="/docs/eve.png?raw=true" style="margin: 5px"> <img src="/docs/home.png?raw=true" style="margin: 5px">

## Configuration
**Before adding this plugin to Homebridge, set up the WeMos D1! Add the SSID/password of your Wi-Fi network to `boot.py` and the correct MQTT parameters to `main.py`.**

| Field name           | Description                                                | Type / Unit    | Default value       | Required? |
| -------------------- |:-----------------------------------------------------------|:--------------:|:-------------------:|:---------:|
| name                 | Name of the accessory                                      | string         | —                   | Y         |
| enableFakeGato       | Enable storing data in Eve Home app                        | bool           | false               | N         |
| fakeGatoStoragePath  | Path to store data for Eve Home app                        | string         | (fakeGato default)  | N         |
| mqttConfig           | Object containing some config for MQTT                     | object         | —                   | Y         |

The mqttConfig object is defined as follows:

| Field name           | Description                                      | Type / Unit  | Default value                   | Required? |
| -------------------- |:-------------------------------------------------|:------------:|:-------------------------------:|:---------:|
| url                  | URL of the MQTT server, must start with mqtt://  | string       | —                               | Y         |
| temperatureTopic     | MQTT topic to which temperature data is sent     | string       | MicroPython_BME280/temperature  | Y         |
| pressureTopic        | MQTT topic to which pressure data is sent        | string       | MicroPython_BME280/pressure     | Y         |
| humidityTopic        | MQTT topic to which humidity data is sent        | string       | MicroPython_BME280/humidity     | Y         |

### Example Configuration

```
{
  "bridge": {
    "name": "Homebridge",
    "username": "XXXX",
    "port": XXXX
  },

  "accessories": [
    {
      "accessory": "MicroPython BME280",
      "name": "Upstairs BME280",
      "enableFakeGato": true,
      "mqtt": {
          "url": "mqtt://192.168.0.38",
          "pressureTopic": "bme280/pressure",
          "temperatureTopic": "bme280/temperature",
          "humidityTopic": "bme280/humidity"
      }
    }
  ]
}
```

## Project Layout

- All things required by Node are located at the root of the repository (i.e. package.json and index.js).
- The rest of the code is in `src`, further split up by language.
  - `micropython` contains `boot.py` (to connect the WeMos D1 to a Wi-Fi network), `main.py` (the main logic of the plugin), and `bme280.py`, a MicroPython driver for the BME280.
  - `js` contains contains a custom characteristic that allows Eve to keep barometric air pressure data.
