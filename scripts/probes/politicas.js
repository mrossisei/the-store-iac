// Built-ins only: executes in the actual Checkout network namespace, no installs.
// Never reads credentials, payloads or application data. Redis PING is read-only.
const net = require('net');
const dgram = require('dgram');
const dns = require('dns');
const [kind, host, portText] = process.argv.slice(1);
const port = Number(portText);
let done = false;
function finish(status, code) {
  if (done) return;
  done = true;
  console.log(JSON.stringify({status, ...(code ? {code} : {})}));
  process.exit(0);
}
setTimeout(() => finish('timeout'), 3000);
if (kind === 'resolve') {
  if (net.isIPv4(host)) {
    console.log(JSON.stringify({status: 'ok', addresses: [host]}));
    process.exit(0);
  }
  dns.resolve4(host, (error, addresses) => {
    if (error) return finish('error', error.code);
    console.log(JSON.stringify({status: 'ok', addresses}));
    process.exit(0);
  });
} else if (kind === 'http') {
  const request = require('http').get(host, response => {
    response.resume();
    response.on('end', () => finish('ok', response.statusCode));
    response.on('aborted', () => finish('error', 'ABORTED_RESPONSE'));
    response.on('error', error => finish('error', error.code));
  });
  request.on('error', error => finish('error', error.code));
} else if (kind === 'dns-udp' || kind === 'dns-tcp') {
  const id = 0x5409;
  const labels = 'kubernetes.default.svc.cluster.local'.split('.');
  const question = Buffer.concat(labels.map(label => Buffer.concat([Buffer.from([label.length]), Buffer.from(label)])));
  const header = Buffer.alloc(12);
  header.writeUInt16BE(id, 0); header.writeUInt16BE(0x0100, 2); header.writeUInt16BE(1, 4);
  const request = Buffer.concat([header, question, Buffer.from([0, 0, 1, 0, 1])]);
  function answer(data) {
    if (data.length < 12 || data.readUInt16BE(0) !== id || !(data[2] & 0x80) || (data[3] & 15) !== 0 || data.readUInt16BE(6) < 1) return finish('error', 'INVALID_DNS_REPLY');
    finish('ok');
  }
  if (kind === 'dns-udp') {
    const socket = dgram.createSocket('udp4');
    socket.on('error', error => finish('error', error.code));
    socket.on('message', (data, peer) => { if (peer.address === host && peer.port === port) answer(data); });
    socket.send(request, port, host);
  } else {
    const socket = net.connect({host, port});
    let received = Buffer.alloc(0);
    socket.on('error', error => finish('error', error.code));
    socket.on('connect', () => {
      const length = Buffer.alloc(2); length.writeUInt16BE(request.length);
      socket.write(Buffer.concat([length, request]));
    });
    socket.on('data', data => {
      received = Buffer.concat([received, data]);
      if (received.length >= 2 && received.length >= received.readUInt16BE(0) + 2) answer(received.subarray(2));
    });
  }
} else if (kind === 'tcp' || kind === 'redis') {
  const socket = net.connect({host, port});
  socket.on('error', error => finish('error', error.code));
  socket.on('connect', () => kind === 'tcp' ? finish('ok') : socket.write('*1\r\n$4\r\nPING\r\n'));
  let received = '';
  socket.on('data', data => {
    received += data.toString();
    if (received.startsWith('+PONG\r\n')) finish('ok');
    else if (received.includes('\r\n')) finish('error', 'INVALID_REDIS_REPLY');
  });
} else {
  finish('error', 'UNKNOWN_PROBE');
}
