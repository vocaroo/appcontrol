const crypto = require("crypto");
const readlineSync = require("readline-sync");
const ipRegex = require("ip-regex");
const getFingerprint = require("./getFingerprint.js");
const {globalDB} = require("./db.js");
const {hostFromServer, updateKnownHostsForServer} = require("./utils.js");

function checkNotAlreadyPresent(recordName, recordValue) {
	const globalServers = globalDB.get("servers").value();

	if (globalServers) {
		for (let serverGroup in globalServers) {
			for (let server of globalServers[serverGroup]) {
				if (server[recordName] && server[recordName] == recordValue) {
					console.log(`Error, ${recordName} of ${recordValue} already present in servers list!`);
					process.exit(1);
				}
			}
		}
	}
}

module.exports = async function cmdAddServer() {
	let ipv4 = readlineSync.question("IPv4 address (optional)\n> ");
	
	if (ipv4 && !ipRegex.v4({exact : true}).test(ipv4)) {
		console.log("Invalid IPv4 address.");
		return;
	}
	
	checkNotAlreadyPresent("ipv4", ipv4);
	
	let ipv6 = readlineSync.question("IPv6 address (optional, recommended)\n> ");
	
	if (ipv6 && !ipRegex.v6({exact : true}).test(ipv6)) {
		console.log("Invalid IPv6 address.");
		return;
	}
	
	checkNotAlreadyPresent("ipv6", ipv6);
	
	if (!ipv4 && !ipv6) {
		console.log("Either an IPv4 or IPv6 address is required! Try again.");
		return;
	}
	
	let hostname = readlineSync.question("Hostname (optional, can be used instead of IP address to identify servers)\n> ");
	checkNotAlreadyPresent("hostname", hostname);
	
	let group = readlineSync.question("Server group (optional, for organisational purposes only)\n> ", {defaultInput : "default"});
	
	// Get the fingerprint
		
	console.log("Getting server fingerprint...");
	
	// make a dummy server object with just the two IPs so we can use hostFromServer to select the correct one
	let fingerprint = await getFingerprint(hostFromServer({ipv4, ipv6}));
	
	let serverInfo = {ipv4, ipv6, hostname, fingerprint, uniqueId : crypto.randomUUID()};
	
	if (!globalDB.has(`servers`).value()) {
		globalDB.set("servers", {})
			.write();
	}
	
	if (!globalDB.has(`servers.${group}`).value()) {
		globalDB.set(`servers.${group}`, [])
			.write();
	}
	
	globalDB.get(`servers.${group}`)
		.push(serverInfo)
		.write();
	
	console.log("Updating known_hosts...");
	updateKnownHostsForServer(serverInfo);
	
	console.log("New server info", {...serverInfo, group});
	console.log("Successfully added new server!");
}
