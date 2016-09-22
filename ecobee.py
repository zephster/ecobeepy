import colorama
from colorama import Fore, Back, Style
import json
import pprint
import requests

pp = pprint.PrettyPrinter(indent=1, width=1, depth=None)
colorama.init(autoreset=True)

class ecobeepy:
	base_url    = 'https://api.ecobee.com'
	config_file = 'ecobeepy.json'
	api_version = '1'

	def __init__(self):
		self._log('ecobeepy by brandon')
		self.client_id = ''
		self.config    = {}
		self.debug     = True

		try:
			self._loadConfig()

			try:
				if self.config['access_token']:
					# todo: check timestamp vs expires_in, refresh or request
					self._getTokens(action='refresh')

				# self.getThermostats()
				self.sendMessage('eat some fucking shit you stupid fucking bitch')
			except KeyError:
				self._getTokens(action='request')
		except FileNotFoundError:
			self._debuglog(Fore.RED + 'no config found - need to authenticate')
			self._auth()

	def _debuglog(self, msg, err=''):
		if self.debug:
			self._log(Back.WHITE + Fore.BLACK + '[debug]' + Back.RESET + Fore.WHITE + ' ' + msg, err)

	def _log(self, msg, err=''):
		print(Fore.CYAN + '[ecobeepy] ' + Fore.WHITE + msg, err, Style.RESET_ALL)

	def _saveConfig(self):
		with open(self.config_file, 'w') as config:
			json.dump(self.config, config)
			self._debuglog('config saved')

	def _loadConfig(self):
		with open(self.config_file, 'r') as config:
			self.config = json.load(config)
			self._log(Fore.GREEN + 'config loaded')

	def __api(self, uri, params=None, headers=None, authed=True, method='get'):
		r = None
		try:
			if not params:
				params = {}
			if not headers:
				headers = {}

			if authed:
				uri = '/' + self.api_version + uri
				headers.update({
					'Content-Type' : 'application/json;charset=UTF-8',
					'Authorization': self.config['token_type'] + ' ' + self.config['access_token']
				})

			if method == 'get':
				r = requests.get(self.base_url + uri, params=params, headers=headers)
			elif method == 'post':
				r = requests.post(self.base_url + uri, data=params, headers=headers)
			else:
				raise Exception('invalid request method')

			if r.status_code != requests.codes.ok:
				r.raise_for_status()

			if r == None:
				return r

			return r.json()
		except Exception as ex:
			self._debuglog(Fore.RED + 'api error:', ex)
			self._debuglog(Fore.RED + r.text)

	def _auth(self):
		try:
			params = {
				'response_type': 'ecobeePin',
				'scope'        : 'smartWrite',
				'client_id'    : self.client_id,
			}

			authdata = self.__api('/authorize', params=params, authed=False)

			if authdata is None:
				raise Exception('invalid auth response')

			pin                      = authdata['ecobeePin']
			self.config['auth_code'] = authdata['code']
			self.config['interval']  = authdata['interval']
			self.config['scope']     = authdata['scope']

			self._log(Fore.GREEN + 'successfully authed')
			self._log(Fore.GREEN + 'PIN: ' + pin + ', expires: ' + str(authdata['expires_in']) + ' minutes')
			self._log(Fore.YELLOW + 'Go to https://www.ecobee.com/consumerportal')
			self._log(Fore.YELLOW + 'Click "My Apps", then "Add Application". Enter PIN, then click Validate.')
			self._log(Fore.YELLOW + 'Re-run this program after you have done the above.')
			self._saveConfig()
		except ValueError as err:
			print("auth error: unable to decode json object", err)
		except TypeError as err:
			print("auth error: typeerror: ", err)
		except Exception as err:
			print('auth error:', err)

	def _getTokens(self, action=None):
		self._debuglog(action + 'ing tokens...')
		tokendata = None

		try:
			if action == 'refresh':
				grant_type   = 'refresh_token'
				param_action = 'refresh_token'
				param_value  = self.config['refresh_token']
			elif action == 'request':
				grant_type   = 'ecobeePin'
				param_action = 'code'
				param_value  = self.config['auth_code']
			else:
				raise Exception('invalid token action')

			params = {
				'grant_type': grant_type,
				'client_id' : self.client_id,
				param_action: param_value,
			}

			tokendata = self.__api('/token', params, authed=False, method='post')

			if tokendata == None:
				raise Exception('invalid token data')

			self._debuglog('got tokens!')
			self.config['access_token']  = tokendata['access_token']
			self.config['refresh_token'] = tokendata['refresh_token']
			self.config['token_type']    = tokendata['token_type']

			# todo: store timestamp
			self.config['expires_in']    = tokendata['expires_in']
			self.config['scope']         = tokendata['scope']
			self._saveConfig()

		except Exception as ex:
			self._log(Fore.RED + 'error ' + action + 'ing tokens:', ex)

			if tokendata != None:
				self._log(Fore.RED + tokendata['error_description'] + ' (' + tokendata['error'] + ')')

	# api methods
	def getThermostats(self):
		self._log('listing thermostats')

		# todo: see https://www.ecobee.com/home/developer/api/documentation/v1/objects/Selection.shtml
		params = {
			'json': (json.dumps({
				'selection': {
					'selectionType'              : 'registered',
					# 'includeAlerts'              : True,
					# 'includeDevice'              : True,
					# 'includeElectricity'         : True,
					# 'includeEquipmentStatus'     : True,
					# 'includeEvents'              : True,
					# 'includeExtendedRuntime'     : True,
					'includeLocation'            : True,
					# 'includeNotificationSettings': True,
					# 'includeOemConfig'           : True,
					# 'includeProgram'             : True,
					'includeRuntime'             : True,
					'includeSensors'             : True,
					# 'includeSettings'            : True,
					# 'includeTechnician'          : True,
					# 'includeUtility'             : True,
					'includeVersion'             : True,
					# 'includeWeather'             : True,
				}
			}))
		}

		try:
			thermostats = self.__api('/thermostat', params)
			pp.pprint(thermostats)
		except Exception as err:
			print('list thermostat error')
			print(err)

	def sendMessage(self, message=None, thermostat_id=None):
		self._log('sending message', message)

		if thermostat_id:
			selectionType  = 'thermostats'
			selectionMatch = thermostat_id
		else:
			selectionType  = 'registered'
			selectionMatch = ''

		params = {
			'selection': {
				'selectionType': selectionType,
				'selectionMatch': selectionMatch
			},
			'functions': [
				{
					'type': 'sendMessage',
					'params': {
						'text': message
					}
				}
			]
		}

		params = json.dumps(params)

		try:
			sent = self.__api('/thermostat', params=params, method='post')

			if sent['status']['code'] == 0:
				self._log(Fore.GREEN + 'success!')
		except Exception as err:
			print('error sending message')
			print(err)

if __name__ == '__main__':
	ecobee = ecobeepy()