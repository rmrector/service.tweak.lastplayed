import collections
import sys
import time
import xbmc
import xbmcaddon

from datetime import datetime

if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json

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

_watch_addon = None
def is_addon_watched():
    global _watch_addon
    if _watch_addon is None:
        if not get_conditional('System.HasAddon(script.module.devhelper)'):
            _watch_addon = False
        else:
            devhelper = xbmcaddon.Addon('script.module.devhelper')
            if devhelper.getSetting('watchalladdons'):
                _watch_addon = True
            else:
                _watch_addon = ADDONID in devhelper.getSetting('watchaddons_list')

    return _watch_addon

def execute_jsonrpc(jsonrpc_command):
    if isinstance(jsonrpc_command, dict):
        jsonrpc_command = json.dumps(jsonrpc_command, ensure_ascii=False)
        if isinstance(jsonrpc_command, unicode):
            jsonrpc_command = jsonrpc_command.encode('utf-8')

    json_result = xbmc.executeJSONRPC(jsonrpc_command)
    return json.loads(json_result, cls=UTF8JSONDecoder)

def get_infolabel(info_label):
    try:
        return xbmc.getInfoLabel(info_label)
    except RuntimeError:
        xbmc.sleep(100)
    return xbmc.getInfoLabel(info_label)

def get_conditional(conditional):
    return xbmc.getCondVisibility(conditional) == 1

def log(message, level=xbmc.LOGDEBUG, tag=None):
    if is_addon_watched() and level < xbmc.LOGNOTICE:
        level_tag = _log_level_tag_lookup[level] + ': ' if level in _log_level_tag_lookup else ''
        level = xbmc.LOGNOTICE
    else:
        level_tag = ''

    if isinstance(message, (dict, list)) and len(message) > 300:
        message = str(message)
    elif isinstance(message, unicode):
        message = message.encode('utf-8')
    elif not isinstance(message, str):
        message = json.dumps(message, cls=UTF8PrettyJSONEncoder)

    addontag = ADDONID if not tag else ADDONID + ':' + tag
    file_message = '%s[%s] %s' % (level_tag, addontag, message)
    xbmc.log(file_message, level)

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

class UTF8PrettyJSONEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        kwargs['skipkeys'] = True
        kwargs['ensure_ascii'] = False
        kwargs['indent'] = 2
        kwargs['separators'] = (',', ': ')
        super(UTF8PrettyJSONEncoder, self).__init__(*args, **kwargs)

    def default(self, obj):
        # Called for objects that aren't directly JSON serializable
        if isinstance(obj, collections.Mapping):
            return dict((key, obj[key]) for key in obj.keys())
        if isinstance(obj, collections.Iterable):
            return list(obj)
        return str(obj)

    def iterencode(self, obj, _one_shot=False):
        for result in super(UTF8PrettyJSONEncoder, self).iterencode(obj, _one_shot):
            if isinstance(result, unicode):
                result = result.encode('utf-8')
            yield result

class UTF8JSONDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super(UTF8JSONDecoder, self).__init__(*args, **kwargs)

    def raw_decode(self, s, idx=0):
        result, end = super(UTF8JSONDecoder, self).raw_decode(s)
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
