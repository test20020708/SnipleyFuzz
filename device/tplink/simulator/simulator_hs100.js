const { Device } = require('../tplink-smarthome-simulator/lib');
const { UdpServer } = require('../tplink-smarthome-simulator/lib');

const devices = [];

devices.push(
    new Device({
      port: 9999,
      address: '192.168.100.20',
      model: 'hs100',
      data: { alias: 'Mock HS100', mac: '50:c7:bf:8f:58:18', deviceId: 'A100' },
    }),
  );

  devices.forEach((d) => {
    d.start();
  });
  
  UdpServer.start();

  console.log("device simulation is successful!")
