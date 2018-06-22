import collections
import os
import sys
import time
import xbmc
import xbmcaddon
from datetime import datetime

oldpython = sys.version_info < (2, 7)
if oldpython:
    import simplejson as json
else:
    import json
newpython = sys.version_info.major == 3

try:
    datetime.strptime('2112-04-01', '%Y-%m-%d')
except TypeError:
    pass

_log_level_tag_lookup = {
    xbmc.LOGDEBUG: 'D',
    xbmc.LOGINFO: 'I'
}

ADDONID = 'service.tweak.lastplayed'

_kodiversion = None
def get_kodi_version():
    global _kodiversion
    if _kodiversion is None:
        json_request = {'jsonrpc': '2.0', 'method': 'Application.GetProperties', 'params': {}, 'id': 1}
        json_request['params']['properties'] = ['version']
        json_result = execute_jsonrpc(json_request)
        if 'result' in json_result:
            _kodiversion = json_result['result']['version']['major']
    return _kodiversion

_main_addon = None
def get_main_addon():
    global _main_addon
    if not _main_addon:
        _main_addon = Addon()
    return _main_addon

_watch_addon = None
def is_addon_watched():
    global _watch_addon
    if _watch_addon is None:
        if not get_conditional('System.HasAddon(script.module.devhelper)'):
            _watch_addon = False
        else:
            devhelper = Addon('script.module.devhelper')
            if devhelper.get_setting('watchalladdons'):
                _watch_addon = True
            else:
                _watch_addon = ADDONID in devhelper.get_setting('watchaddons_list')

    return _watch_addon

def datetime_now():
    try:
        return datetime.now()
    except ImportError:
        xbmc.sleep(50)
        return datetime_now()

def datetime_strptime(date_string, format_string):
    try:
        return datetime.strptime(date_string, format_string)
    except TypeError:
        try:
            return datetime(*(time.strptime(date_string, format_string)[0:6]))
        except ImportError:
            xbmc.sleep(50)
            return datetime_strptime(date_string, format_string)

def execute_jsonrpc(jsonrpc_command):
    if isinstance(jsonrpc_command, dict):
        jsonrpc_command = json.dumps(jsonrpc_command)

    json_result = xbmc.executeJSONRPC(jsonrpc_command)
    return json_loads(json_result)

def json_loads(json_string):
    args = {} if newpython else {'cls': UTF8JSONDecoder}
    return json.loads(json_string, **args)

def json_dumps(json_obj, pretty=False):
    if not pretty:
        return json.dumps(json_obj)
    cls = PrettyJSONEncoder if newpython else UTF8PrettyJSONEncoder
    return json.dumps(json_obj, cls=cls)

def get_conditional(conditional):
    return xbmc.getCondVisibility(conditional)

def log(message, level=xbmc.LOGDEBUG, tag=None):
    if is_addon_watched() and level < xbmc.LOGNOTICE:
        # Messages from this add-on are being watched, elevate to NOTICE so Kodi logs it
        level_tag = _log_level_tag_lookup[level] + ': ' if level in _log_level_tag_lookup else ''
        level = xbmc.LOGNOTICE
    else:
        level_tag = ''

    if isinstance(message, (dict, list)) and len(message) > 300:
        message = str(message)
    elif isinstance(message, unicode):
        message = message.encode('utf-8')
    elif not isinstance(message, str):
        message = json_dumps(message, True)

    addontag = ADDONID if not tag else ADDONID + ':' + tag
    file_message = '%s[%s] %s' % (level_tag, addontag, message)
    xbmc.log(file_message, level)

class Addon(xbmcaddon.Addon):
    def __init__(self, *args, **kwargs):
        super(Addon, self).__init__()
        self.addonid = self.getAddonInfo('id')
        self.version = self.getAddonInfo('version')
        self.path = self.getAddonInfo('path')
        self.datapath = self.getAddonInfo('profile')
        self.resourcespath = os.path.join(xbmc.translatePath(self.path).decode('utf-8'), u'resources')
        if not os.path.isdir(self.resourcespath):
            self.resourcespath = None

    def get_setting(self, settingid):
        result = str(self.getSetting(settingid))
        if result == 'true':
            result = True
        elif result == 'false':
            result = False
        elif settingid.endswith('_list'):
            result = [addon.strip() for addon in result.split('|')]
            if len(result) == 1 and not result[0]:
                result = []
        return result

    def set_setting(self, settingid, value):
        if settingid.endswith('_list') and not isinstance(value, basestring) and isinstance(value, collections.Iterable):
            value = '|'.join(value)
        elif not isinstance(value, basestring):
            value = str(value)
        self.setSetting(settingid, value)

class ObjectJSONEncoder(json.JSONEncoder):
    # Will still flop on circular objects
    def __init__(self, *args, **kwargs):
        kwargs['skipkeys'] = True
        super(ObjectJSONEncoder, self).__init__(*args, **kwargs)

    def default(self, obj):
        # Called for objects that aren't directly JSON serializable
        if isinstance(obj, collections.Mapping):
            return dict((key, obj[key]) for key in obj.keys())
        if isinstance(obj, collections.Sequence):
            return list(obj)
        if callable(obj):
            return str(obj)
        try:
            result = dict(obj.__dict__)
            result['* objecttype'] = str(type(obj))
            return result
        except AttributeError:
            pass # obj has no __dict__ attribute
        result = {'* repr': repr(obj)}
        result['* objecttype'] = str(type(obj))
        return result

class PrettyJSONEncoder(ObjectJSONEncoder):
    def __init__(self, *args, **kwargs):
        kwargs['ensure_ascii'] = False
        kwargs['indent'] = 2
        kwargs['separators'] = (',', ': ')
        super(PrettyJSONEncoder, self).__init__(*args, **kwargs)

class UTF8PrettyJSONEncoder(PrettyJSONEncoder):
    def iterencode(self, obj, _one_shot=False):
        for result in super(UTF8PrettyJSONEncoder, self).iterencode(obj, _one_shot):
            if isinstance(result, unicode):
                result = result.encode('utf-8')
            yield result

class UTF8JSONDecoder(json.JSONDecoder):
    def raw_decode(self, s, idx=0):
        args = (s,) if oldpython else (s, idx)
        result, end = super(UTF8JSONDecoder, self).raw_decode(*args)
        result = self._json_unicode_to_str(result)
        return result, end

    def _json_unicode_to_str(self, jsoninput):
        if isinstance(jsoninput, dict):
            return dict((self._json_unicode_to_str(key), self._json_unicode_to_str(value)) for key, value in jsoninput.iteritems())
        elif isinstance(jsoninput, list):
            return [self._json_unicode_to_str(item) for item in jsoninput]
        elif isinstance(jsoninput, unicode):
            return jsoninput.encode('utf-8')
        else:
            return jsoninput
