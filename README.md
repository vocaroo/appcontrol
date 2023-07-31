# WHAT?

AppControl is a tool for the quick deployment of client side web apps (such as those from create-react-app) and NodeJS server apps to Ubuntu servers.

It provides simple easy to use commands to build and deploy your apps, automatically generating Nginx server configuration and Letsencrypt SSL certificates.

_Deploying to any Debian derived SystemD supporting OS might work but this is untested._

# Installation

AppControl is a NodeJS app. First install NodeJS, then install AppControl with:

`npm install -g appcontrol`

# Basic tutorial

This shows how to deploy a static web app to a single server.

1. Create a new web app (e.g. using create-react-app or similar)
2. Generate a ed25519 key pair, if you don't already have one, using `appcontrol keygen`
3. Provision a new Ubuntu server using this ed25519 key.
4. Add the server to appcontrol's database: `appcontrol addserver`
5. In the directory above your app, create a basic deployment config: `appcontrol init`.
6. Create a release of all your apps in their current state: `appcontrol release`
7. Deploy to the default "production" deployment target: `appcontrol deploy production`

et voila! Your app should now be accessible from the interwebs. You can also combine the last two steps using the command `appcontrol quickrelease production` to perform a release and deploy in one step.

Some further things you might want to do / be aware of:

- `appcontrol init` will create the deploy config file `appcontrol.json` in the current directory, and also an app specific config file `app.json` in your app's directory
- make sure your app's domain has its DNS records propagated and pointing to the desired server before deploying, otherwise getting SSL certificates will fail (alternatively, appcontrol supports Letsencrypt DNS validation, but that requires a bit more configuration)
- if your app has a build step, edit the `app.json` file in your app's directory to set the correct `buildCmd` and `buildDir`.  _create-react-apps are currently autodetected and will use the default CRA build command_.

# Future of Appcontrol

AppControl is very much a work in progress. There may be breaking changes in the future!

## Todo

- clean up commands (various things are not cleaned up that should be, e.g. certificates will keep being requested for a domain even if you stop using that domain or change from HTTP to DNS verification)
- various server management commands are needed (for example to list all apps on a server, and check running app status)
- release rollback command (for now you can: 1. delete the most recent release, 2. decrement latestReleaseNum in .appcontrol/database.json, and re-deploy... )
- (maybe) support for other server runtimes such as NextJS, Python or PHP.
- (maaaybe) some kind of docker app support

# Command overview

| command | description |
| --- | --- |
| `appcontrol info` | Show info about deployment |
| `appcontrol init` | Create a basic deployment config in the current directory |
| `appcontrol keygen` | Generate an ed25519 key pair at the location specified in your config, or ~/.ssh otherwise |
| `appcontrol addserver` | Add a server definition to the global database |
| `appcontrol reset <server>` | This must be called if a host or control server has been reinstalled or reprovisioned. Will get the new fingerprint and prepare to re-sync some control scripts |
| `appcontrol release` | Create a numbered release |
| `appcontrol deploy <target>` | Deploy latest release to a named target, e.g. staging or production |
| `appcontrol quickrelease <target>` | Release and deploy in one step |
| `appcontrol get-fingerprint <hostIP>` | Get the ed25519 fingerprint of the specified host, only useful if  you manually edit the server definitions |

# Configuration files and project structure

## Project structure

AppControl expects all apps in a given deployment to be stored in the same "project directory", adjacent to your project's deployment config file `appcontrol.json`. AppControl will create the hidden directory `.appcontrol` in your project directory, which contains some deployment state and key pairs, and by default, the built releases of your apps.

## Project configuration

There are three main configuration files:

- `appcontrol.json` in your project's directory. This stores information regarding what apps in your project will be deployed to what servers for what named deployments, and other per project config including any environmental variables for your app's different deployments. Also referred to as the "deploy config".
- `app.json` in an app's directory. The presence of an app.json file indicates that this folder contains an app that should be released and deployed via AppControl. The app.json can contain some configuration specific to that app, such as a build command.
- `~/.appcontrol` in your home directory. This contains the definitions of all servers you add to appcontrol via `appcontrol addserver` (IP addresses, fingerprints), plus it may contain some global config which you want to apply to all your projects.

### Environmental variables

Environmental variables can be specified in many different locations:

- an individual app's `app.json`
- global env in `appcontrol.json` (applying to all apps across all deployments)
- env specified in a specific deployment block (e.g. staging, production), applying to all servers and apps in that deployment
- env specified for a specific app within a server block

All env is overloaded in the order listed above, with latterly specified env taking precedence. As well as simple "env" blocks in the config, there are more advanced forms…

| property | description |
| --- | --- |
| env | Simple key-value dictionary of environmental variables to be applied to all apps. |
| envClient | Env to be applied to all client side web apps only. |
| envServer | Env to be applied to all server side apps only. |
| envShared | Env applied to a group of named apps. |
| envApp | Env applied only to specific named apps. |

Within the same block, the different env, envClient, envServer, etc, take precedence as in the order given above. Please see the examples below to see how to use env blocks correctly.

#### AppControl environmental variables

AppControl provides server apps with some utility env vars:

| environmental variable | description |
| --- | --- |
| PORT | All server apps will have a PORT variable set, which their domain and webPath will be routed too. Your server apps must use this port to listen on. If there are multiple instances of the app (e.g. an instance per CPU), they will each have a different listen port. Ports may change across restarts of your apps! |
| APP_DATA_DIR | The path of a directory that your app has write access to and should use to store any data. Apps in the same dataGroup will be passed the same APP_DATA_DIR so they can share data |
| APP_LOG_DIR | Similar to above, but a directory within `/var/log` that your app can write to |
| APP_TEMP_DIR | Same as above, but a directory within `/tmp` |

#### Env block examples

```json
"env" : {
	"TEST_CDN" : "https://cdn.test-all-apps.com"
},

"envClient" : {
	"TEST_CDN" : "https://cdn.test-client-apps-only.com"
},

"envServer" : {
	"TEST_CDN" : "https://cdn.test-server-apps-only.com"
},

"envShared" : [
	{
		"apps" : ["my-app-1", "my-app-2"],
		"env" : {
			"TEST_CDN" : "https://cdn.my-app-1-and-2-only.com"
		}
	}
],

"envApp" : {
	"my-app-99" : {
		"TEST_CDN" : "https://cdn.my-app-99-only.com"
	}
}
```

#### Injecting env vars into web apps

Environmental variables can be injected into web apps using a very basic templating mechanism. Unlike some systems, with AppControl these are injected *after* the build step, and not during it. This is so the exact same build can be deployed to different targets, and with different configuration.
There are two ways env vars can be injected; either individual variables or all at once as a JSON string.

| search and replace string | description |
| --- | --- |
| ###APPCONTROL_JSON_ENV### | This special string will be replaced with a JSON object string containing all the env vars for your app |
| ###APPCONTROL_ENV_MYVAR### | In this example, a single env var "MYVAR" will be injected |

In order for a web app to have env vars injected the property `injectEnv` must be present in its `app.json`, and must be set to a regex that will match any file names in which you want to have env injected (for example, `"\\.(js|html)$"` to match all js or html files)

Example injecting env into a HTML script tag under the global "process.env":

`<script>var process={env : ###APPCONTROL_JSON_ENV###}</script>`

Example injecting a single env var named "MYCDN", a custom CDN string, into HTML:

`<img src="###APPCONTROL_ENV_MYCDN###/cat.jpg">`

Those examples would require the following `app.json`, assuming both files end in .html:

```json
{
	"injectEnv" : "\\.html$"
}
```

##### Webpack example

If you are using webpack, you might want to have separate webpack development and production configurations. You can then use webpack's htmlPluginOptions like thus:

`<script>var process={env : <%= htmlWebpackPlugin.options.appcontrolJsonEnv %>}</script>`

Then, in your development webpack config you can set whatever custom env you want under `appcontrolJsonEnv`, and in your production config you can instead output only the string "###APPCONTROL_JSON_ENV###" which will be replaced during deployment by AppControl with your production env.

### app.json

Everything in the app.json is optional. An empty app.json indicates a client side web app with no build step. The app.json file will be skipped during deployment.

#### Example

```json
{
	"runtime" : "node:20",
	"main" : "server.js",
	"buildCmd" : "npm build",
	"buildPath" : "build/"
	"injectEnv": "\\.(js|html)$"
	"env" : {
		"NODE_OPTIONS" : "--max-old-space-size=800"
	}
}
```

#### Properties

| property | description |
| --- | --- |
| main | The main file of an app. The presence of `main` indicates that this is a server side app such as a Node API or daemon process. If `main` is omitted, the app will be considered a client side web app and its files will be made available via the nginx server. |
| runtime | The runtime, if this is a server side app. Currently only NodeJS is supported. This can either be `node` to use the latest node version, or a specific major version can be specified like so: `node:20` |
| buildCmd | An optional build command that will be run during release. If no buildCmd is specified, the entire app directory will be copied as-is. |
| buildPath | Optional build path, `build` by default. After running the buildCmd, the contents of buildPath will be copied to the release. |
| injectEnv | Environmental variables can be injected into web apps after they have been built. This regex specifies which files will have these injected. See also the section on environmental variables. |
| env | Any environmental variables. The values must be simple strings. They will be overridden by any identically named env vars in the deploy config. |

### appcontrol.json

#### Minimal example

This deploys a single web app "example-basic-html" to the server 192.168.1.99, with the domain and path `example.com/example-basic-html`, and will use Letsencrypt's default HTTP verification method for getting the SSL certificate.

```json
{
	"deployments" : {
		"staging" : {
			"servers" : {
				"192.168.1.99" : {
					"apps" : [
						{
							"app" : "example-basic-html",
							"domain" : "example.com",
							"webPath" : "/example-basic-html"
						}
					]
				}
			}
		}
	}
}
```

#### Very Long Example

This uses the Letsencrypt DNS verification method along with an alias domain, and deploys to the server with the hostname _appcontrol-test_ (named when adding the server to appcontrol). You can of course have more than one server under the "servers" block, but that would make this a very very long example.

```json
{
	"letsencrypt" : {
		"dns_hook" : "dns_gandi_livedns",
		"challenge_alias_domain" : "mydomain.com",
		"env" : {
			"GANDI_LIVEDNS_KEY" : "1234567890"
		}
	},
	
	"env" : {
		"EXAMPLE_VAR" : "this var present for all apps across all deployments"
	},
	
	"deployments" : {
		"staging" : {
			"masterServer" : "appcontrol-test",
			
			"env" : {
				"EXAMPLE_VAR" : "present for all apps in this staging deployment"
			},
			
			"envClient" : {
				"CLIENT_VAR" : "present for all web apps in staging"
			},
			
			"envServer" : {
				"SERVER_VAR" : "present for all server apps in staging"
			},
			
			"envShared" : [
				{
					"apps" : ["example-basic-html", "example-node-server"],
					"env" : {
						"EXAMPLE_VAR" : "present for just the apps listed above"
					}
				}
			],
			
			"envApp" : {
				"example-node-server" : {
					"EXAMPLE_VAR" : "present for this one named app, across all servers in this deployment"
				}
			},
			
			"servers" : {
				"appcontrol-test" : {
					"redirects" : [
						{
							"domain" : "old.example.com",
							"destination" : "https://new.example.com/$request_uri",
							"code" : 301
						},
						{
							"domain" : "old.example.com",
							"regex" : "^/page/(.+)$",
							"destination" : "https://new.example.com/new_page/$1",
							"code" : 301
						}
					],
					"apps" : [
						{
							"app" : "example-basic-html",
							"domain" : "example.com",
							"webPath" : "/example-basic-html"
						},
						{
							"app" : "example-node-server",
							"domain" : "example.com",
							"webPath" : "/example-node-server",
							"instancesPerCPU" : 1,
							"dataGroup" : "nodeservergroup",
							"env" : {
								"EXAMPLE_VAR" : "env for this app only on this specific server"
							}
						},
						{
							"app" : "example-node-daemon"
						}
					]
				}
			}
		}
	}
}
```

#### Properties

##### Top level

| property | description |
| --- | --- |
| name | Optional. The project's name. If omitted, the name of the project folder will be used |
| releaseDIr | Optional. By default, releases will be stored in `.appcontrol/releases` within your project. |
| letsencrypt | For most cases, this should be omitted, and AppControl will get certificates using the Letsencrypt HTTP challenge method. This does require that your DNS records are already set up and propagated and pointing your domains to your appcontrol servers. If that's not the case, you can use the DNS API. |
| env* | Any of the env* properties can be here. Please see the environmental variables section. |
| masterServer | A server to be used as the master server, for all deployments. Can be specified by IP address or hostname (as passed to `appcontrol addserver`). The master server receives the released apps and in turn propagates them to other host servers. It also handles SSL certificate renewal and other things. This can be omitted, in which case the first server in a deployment block will be used as the master. If you have only one server, that will be both the master and the host. |
| deployments | The deployments of this project. A deployment is a named collection of servers and the apps that will be deployed to them. For example, staging or production. There can be any amount of named child objects for however many deployments you have. |

##### Letsencrypt block

These properties can be present in the letsencrypt block. These configuration options relate to using the Letsencrypt DNS API to get certs. This is useful if for whatever reason you don't yet have the correct DNS records set up for your servers and so can't use the simpler HTTP verification.

| property | description |
| --- | --- |
| dns_hook | The name of an [Acme.sh DNS API plugin](https://github.com/acmesh-official/acme.sh/wiki/dnsapi). Appcontrol uses [acme.sh](https://github.com/acmesh-official/acme.sh) for getting SSL certs. |
| challenge_alias_domain | In case you want to use [Acme.sh's alias mode](https://github.com/acmesh-official/acme.sh/wiki/DNS-alias-mode) |
| env | Env to be passed to Acme.sh when issuing certificates. This might include credentials for a DNS API plugin. |

##### Deployment blocks

A deployment block can contain the following properties:

| property | description |
| --- | --- |
| letsencrypt | A letsencrypt block here will override any specified at the top level. |
| masterServer | A masterServer specified here will override any specified at the top level. |
| env* | Any of the env* properties can be here. Please see the environmental variables section. |
| servers | This object will contain all the servers in this deployment, as key value pairs where the key is the IP address or hostname, and the value is a server block. |

##### Server block

A server IP address or hostname may be used as a property of the deployment block, and the object it points to will be a server block. A server block may contain:

| property | description |
| --- | --- |
| apps | A list of app objects, which define each app that will be present on this server. |
| redirects | A list of redirect objects, which allow you to redirect one domain or an arbitrary regex to another location. This is kind of hackish and requires some understanding of Nginx to use. |

##### App blocks

| property | description |
| --- | --- |
| app | App name; the name of the folder containing the app to be released and deployed. |
| domain | Domain name for the app. A server app with no domain name will have no routing and will be a server daemon that is not accessible to the public. |
| webPath | Path on that domain to serve the app from. Multiple apps can be served from a single domain using different paths. Defaults to the root "/". |
| instancesPerCPU | For server apps, the number of instances to start per CPU. For only a single instance per server, set to zero or omit (the default). |
| dataGroup | Apps of a deployment within the same named datagroup will have the same user on the server and will have access to the same data and log directories. |
| env | Any more env vars, this is the most specific and will take precedence over any env vars specified elsewhere. |

##### Redirect blocks

These blocks should be considered experimental and used carefully, as putting the wrong thing as a regex or destination could easily break your nginx config. Redirecting a domain that is already used by an app might also cause fun problems. It's recommended to check the generated nginx config carefully on a test server before deploying to production. You have been warned. 

These are mostly intended for when you move a website or API to a new domain and need to redirect from the old one, with the old domain being obsolete and having no apps using it. See the long `appcontrol.json` example earlier in the docs.

| property | description |
| --- | --- |
| domain | The source domain to be redirected. |
| regex | An optional path matching regex. If omitted, will redirect the entire domain at the root level. |
| destination | The target URL to redirect to. May include nginx things such as `$request_uri` or `$1` for regex matches. |
| code | The redirect code, e.g. `301`. |

### The global .appcontrol.json

The file `.appcontrol.json` in your home directory is more of a database that generally shouldn't be edited, however you can add some global things here.

| property | description |
| --- | --- |
| email | The email address used by letsencrypt |
| releaseDir | You can set a global release dir for all projects to be released to. |
| servers | Lists of all servers added to appcontrol, organised by a group name. It's recommended to add to this by using the command `appcontrol addserver` rather than editing directly. |

# That's all folks

Congratulations on scrolling this far.