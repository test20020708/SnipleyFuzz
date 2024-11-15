const { Device } = require('../tplink-smarthome-simulator/lib');
const { UdpServer } = require('../tplink-smarthome-simulator/lib');

const devices = [];

devices.push(
    new Device({
      port: 9999,
      address: '192.168.100.21',
      model: 'hs110',
      data: { alias: 'Mock HS110', mac: '50:c7:bf:8f:58:19', deviceId: 'A110' },
    }),
  );

  devices.forEach((d) => {
    d.start();
  });
  
  UdpServer.start();

  console.log("device simulation is successful!")