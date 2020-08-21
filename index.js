const moment = require('moment'); // Time formatting
const mqtt = require('mqtt'); // MQTT client
const os = require('os'); // Hostname

var Service, Characteristic;
var CustomCharacteristic;
var FakeGatoHistoryService;

module.exports = (homebridge) => {
  Service = homebridge.hap.Service;
  Characteristic = homebridge.hap.Characteristic;
  CustomCharacteristic = require('./src/js/customcharacteristic.js')(homebridge);
  FakeGatoHistoryService = require('fakegato-history')(homebridge);

  homebridge.registerAccessory('homebridge-micropython-bme280', 'MicroPython BME280', BME280Accessory);
}

function BME280Accessory(log, config) {
  // Load configuration from files
  this.log = log;
  this.displayName = config['name'];
  this.timeout = config['timeout'] || 5;
  this.enableFakeGato = config['enableFakeGato'] || false;
  this.fakeGatoStoragePath = config['fakeGatoStoragePath'];
  this.mqttConfig = config['mqtt'];

  // Services
  let informationService = new Service.AccessoryInformation();
  informationService
    .setCharacteristic(Characteristic.Manufacturer, 'Bosch')
    .setCharacteristic(Characteristic.Model, 'BME280')
    .setCharacteristic(Characteristic.SerialNumber, `${os.hostname}-${this.mqttConfig.temperatureTopic.split('/').shift()}`)
    .setCharacteristic(Characteristic.FirmwareRevision, require('./package.json').version);

  let temperatureService = new Service.TemperatureSensor();
  temperatureService.addCharacteristic(CustomCharacteristic.AtmosphericPressureLevel);
  let humidityService = new Service.HumiditySensor();

  this.informationService = informationService;
  this.temperatureService = temperatureService;
  this.humidityService = humidityService;

  // Start FakeGato for logging historical data
  if (this.enableFakeGato) {
    this.fakeGatoHistoryService = new FakeGatoHistoryService('weather', this, {
      storage: 'fs',
      folder: this.fakeGatoStoragePath
    });
  }

  this.setUpMQTT();

  // Assume error if five minutes pass with no update
  setInterval(() => {
    if (moment().diff(this.lastUpdated, 'minutes') >= this.timeout) {
      this.log(`No messages received for ${this.timeout} minute(s), assuming error!`);
      this.temperatureService.getCharacteristic(Characteristic.CurrentTempererature)
        .updateValue(Error());
      this.humidityService.getCharacteristic(Characteristic.CurrentRelativeHumidity)
        .updateValue(Error());
    }
  }, 30000);
}

BME280Accessory.prototype.onMQTTMessage = function(topic, message) {
  this.log(`Received measurement: ${parseInt(message)} on topic ${topic}`);
  switch (topic) {
    case this.pressureTopic: {
      this.temperatureService.getCharacteristic(CustomCharacteristic.AtmosphericPressureLevel)
        .updateValue(parseInt(message));
      if (this.enableFakeGato) {
        this.fakeGatoHistoryService.addEntry({
          time: moment().unix(),
          pressure: parseInt(message),
        });
      }
      break;
    }
    case this.temperatureTopic: {
      this.temperatureService.getCharacteristic(Characteristic.CurrentTemperature)
        .updateValue(parseInt(message));
      if (this.enableFakeGato) {
        this.fakeGatoHistoryService.addEntry({
          time: moment().unix(),
          temp: parseInt(message),
        });
      }
      break;
    }
    case this.humidityTopic: {
      this.humidityService.getCharacteristic(Characteristic.CurrentRelativeHumidity)
        .updateValue(parseInt(message));
      if (this.enableFakeGato) {
        this.fakeGatoHistoryService.addEntry({
          time: moment().unix(),
          humidity: parseInt(message),
        });
      }
      break;
    }
    default:
      this.log(`Unknown topic ${topic}`);
  }
  this.lastUpdated = moment();
}

// Sets up MQTT client based on config loaded in constructor
BME280Accessory.prototype.setUpMQTT = function() {
  if (!this.mqttConfig) {
    this.log.error('No MQTT config found');
    return;
  }

  this.mqttUrl = this.mqttConfig.url;
  this.pressureTopic = this.mqttConfig.pressureTopic || 'MicroPython_BME280/pressure';
  this.temperatureTopic = this.mqttConfig.temperatureTopic || 'MicroPython_BME280/temperature';
  this.humidityTopic = this.mqttConfig.humidityTopic || 'MicroPython_BME280/humidity';

  this.mqttClient = mqtt.connect(this.mqttUrl);

  this.mqttClient.on('connect', () => {
    this.log(`MQTT client connected to ${this.mqttURL}`);
    this.mqttClient.subscribe(this.pressureTopic, (err) => {
      if (!err) {
        this.log(`MQTT client subscribed to ${this.pressureTopic}`);
      }
    });
    this.mqttClient.subscribe(this.temperatureTopic, (err) => {
      if (!err) {
        this.log(`MQTT client subscribed to ${this.temperatureTopic}`);
      }
    });
    this.mqttClient.subscribe(this.humidityTopic, (err) => {
      if (!err) {
        this.log(`MQTT client subscribed to ${this.humidityTopic}`);
      }
    });
  });

  this.mqttClient.on('message', (topic, message) => {
    this.onMQTTMessage(topic, message)
  }); 

  this.mqttClient.on('error', (err) => {
    this.log(`MQTT client error: ${err}`);
    client.end();
  });
}

BME280Accessory.prototype.getServices = function() {
  if (this.enableFakeGato) { 
    return [this.informationService,
            this.temperatureService,
            this.humidityService,
            this.fakeGatoHistoryService];
  } else {
    return [this.informationService,
            this.temperatureService,
            this.humidityService];
  }
}

