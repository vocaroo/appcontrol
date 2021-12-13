from pathlib import Path
import constants

def getCertPrivkeyPath(domain):
	return constants.HOSTSERVER_CERTS_DIR + "/" + domain + ".key.pem"

def getCertFullchainPath(domain):
	return constants.HOSTSERVER_CERTS_DIR + "/" + domain + ".fullchain.pem"

def fromTemplate(templateName, substitutions):
    template = Path(constants.HOSTSERVER_SCRIPTS_DIR + "/nginx-templates/" + templateName).read_text()
    for original, replacement in substitutions.items():
        template = template.replace(original, replacement)
    return template
