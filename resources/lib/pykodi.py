import collections
import sys
import xbmc
import xbmcaddon

from datetime import datetime

if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json

_addonid = None

def _get_addonid():
    global _addonid
    if not _addonid:
        _addonid = xbmcaddon.Addon().getAddonInfo('id')
    return _addonid

def execute_jsonrpc(jsonrpc_command):
    if isinstance(jsonrpc_command, dict):
        jsonrpc_command = json.dumps(jsonrpc_command, ensure_ascii=False)
        if isinstance(jsonrpc_command, unicode):
            jsonrpc_command = jsonrpc_command.encode('utf-8')

    json_result = xbmc.executeJSONRPC(jsonrpc_command)
    return json.loads(json_result, cls=UTF8JSONDecoder)

def log(message, level=xbmc.LOGDEBUG):
    if isinstance(message, (dict, list, tuple)):
        message = json.dumps(message, skipkeys=True, ensure_ascii=False, indent=2, cls=LogJSONEncoder)
        if isinstance(message, unicode):
            message = message.encode('utf-8')
    elif isinstance(message, unicode):
        message = message.encode('utf-8')
    elif not isinstance(message, str):
        message = str(message)

    file_message = '[%s] %s' % (_get_addonid(), message)
    xbmc.log(file_message, level)

def first_datetime():
    count = 0
    while count < 50:
        try:
            # Threading can make the first call an ass, just keep trying until it works
            datetime.now()
        except ImportError, ex:
            log('ImportError with datetime.now() "%s"' % ex)
            xbmc.sleep(100)
        else:
            return True
        count += 1
    return False

class LogJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, collections.Mapping):
            return dict((key, obj[key]) for key in obj.keys())
        if isinstance(obj, collections.Iterable):
            return list(obj)
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)

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
