import collections
import json
import time
import xbmc
from datetime import datetime

try:
    # REVIEW: is this necessary in Kodi 19 / Python 3?
    datetime.strptime('2112-04-01', '%Y-%m-%d')
except TypeError:
    pass

_log_level_tag_lookup = {
    xbmc.LOGDEBUG: 'D',
    xbmc.LOGINFO: 'I'
}

ADDONID = 'service.tweak.lastplayed'

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
    return json.loads(json_string)

def json_dumps(json_obj, pretty=False):
    if not pretty:
        return json.dumps(json_obj)
    return json.dumps(json_obj, cls=PrettyJSONEncoder)

def get_conditional(conditional):
    return xbmc.getCondVisibility(conditional)

def log(message, level=xbmc.LOGDEBUG, tag=None):
    if isinstance(message, (dict, list)) and len(message) > 300:
        message = str(message)
    elif not isinstance(message, str):
        message = json_dumps(message, True)

    addontag = ADDONID if not tag else ADDONID + ':' + tag
    file_message = '[{}] {}'.format(addontag, message)
    xbmc.log(file_message, level)

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
        except AttributeError: # obj has no __dict__ attribute
            result = {'* repr': repr(obj)}
        result['* objecttype'] = str(type(obj))
        return result

class PrettyJSONEncoder(ObjectJSONEncoder):
    def __init__(self, *args, **kwargs):
        kwargs['ensure_ascii'] = False
        kwargs['indent'] = 2
        kwargs['separators'] = (',', ': ')
        super(PrettyJSONEncoder, self).__init__(*args, **kwargs)
