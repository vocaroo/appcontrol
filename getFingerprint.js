const util = require("util");
const child_process = require("child_process");
const exec = util.promisify(child_process.exec);

module.exports = async function(hostIP) {
	const {stdout, stderr} = await exec("ssh-keyscan -H -t ed25519 " + hostIP);

	let match = stdout.toString().match(/ssh-ed25519 ([a-zA-Z0-9/]+)/);

	if (match) {
		let fingerprint = match[1];
		console.log("Fingerprint is:");
		console.log(" " + fingerprint);
	} else {
		if (stdout) {
			console.log(stdout.toString().trim());
		}

		if (stderr) {
			console.log(stderr.toString().trim());
		}

		console.log("Error, could not get fingerprint!");
	}
}
