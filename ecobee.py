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

	def __init__(self, auth_code=None, pin=None):
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
					# pass
			except KeyError:
				self._getTokens(action='request')
		except FileNotFoundError:
			self._debuglog(Fore.RED + 'no config found - need to authenticate')
			self._auth()

	def _debuglog(self, msg):
		if self.debug:
			self._log(Back.WHITE + Fore.BLACK + '[debug]' + Back.RESET + Fore.WHITE + ' ' + msg)

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

	def _auth(self):
		url    = self.base_url + '/authorize'
		params = {
			'response_type': 'ecobeePin',
			'client_id'    : self.client_id,
			'scope'        : 'smartWrite',
		}

		try:
			r = requests.get(url, params=params)

			if r.status_code != requests.codes.ok:
				r.raise_for_status()

			rjson                    = r.json()
			pin                      = rjson['ecobeePin']
			self.config['auth_code'] = rjson['code']
			self.config['interval']  = rjson['interval']
			self.config['scope']     = rjson['scope']

			self._log(Fore.GREEN + 'successfully authed')
			self._log(Fore.GREEN + 'PIN: ' + pin + ', expires: ' + str(rjson['expires_in']) + ' minutes')
			self._log(Fore.YELLOW + 'Go to https://www.ecobee.com/consumerportal')
			self._log(Fore.YELLOW + 'Click "My Apps", then "Add Application". Enter PIN, then click Validate.')
			self._log(Fore.YELLOW + 'Re-run this program after you have done the above.')
			self._saveConfig()
		except ValueError as err:
			print("unable to decode json object", err)
		except TypeError as err:
			print("typeerror: ", err)
		except Exception as err:
			print('uh oh something bad happened during auth:', err)

	def _getTokens(self, action=None):
		self._debuglog(action + 'ing tokens...')
		url   = self.base_url + '/token'
		rjson = None

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

			# request = ecobeePin, refresh = refresh_token
			params = {
				'grant_type': grant_type,
				param_action: param_value,
				'client_id' : self.client_id
			}

			r     = requests.post(url, params=params)
			rjson = r.json()

			if r.status_code != requests.codes.ok:
				r.raise_for_status()

			self._debuglog('got tokens!')
			self.config['access_token']  = rjson['access_token']
			self.config['refresh_token'] = rjson['refresh_token']
			self.config['token_type']    = rjson['token_type']

			# todo: store timestamp. expires_in is seconds? docs dont say, lol
			self.config['expires_in']    = rjson['expires_in']
			self.config['scope']         = rjson['scope']
			self._saveConfig()
		except Exception as err:
			self._log(Fore.RED + 'error ' + action + 'ing tokens:', err)

			if rjson != None:
				self._log(Fore.RED + rjson['error_description'] + ' (' + rjson['error'] + ')')


	# api methods
	def listThermostats(self):
		self._log('listing thermostats')
		url     = self.base_url + '/1/thermostat'
		headers = {
			'Content-Type': 'application/json;charset=UTF-8',
			'Authorization': self.config['token_type'] + ' ' + self.config['access_token']
		}

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
			r     = requests.get(url, params=params, headers=headers)
			rjson = r.json()
			pp.pprint(rjson)
		except Exception as err:
			print('list thermostat error')
			print(err)


if __name__ == '__main__':
	ecobee = ecobeepy()
	ecobee.listThermostats()