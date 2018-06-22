from lib.libs import pykodi
from lib.libs.pykodi import log

# [0] method part
typemap = {'movie': ('Movie',),
    'episode': ('Episode',),
    'musicvideo': ('MusicVideo',)}

def get_details(dbid, mediatype):
    assert mediatype in typemap

    json_request = get_base_json_request('VideoLibrary.Get{0}Details'.format(typemap[mediatype][0]))
    json_request['params'][mediatype + 'id'] = dbid
    json_request['params']['properties'] = ['lastplayed', 'title', 'dateadded', 'playcount', 'resume']

    json_result = pykodi.execute_jsonrpc(json_request)

    result_key = mediatype + 'details'
    if check_json_result(json_result, result_key, json_request):
        return json_result['result'][result_key]

def set_item_details(dbid, mediatype, **details):
    assert mediatype in typemap

    json_request = get_base_json_request('VideoLibrary.Set{0}Details'.format(typemap[mediatype][0]))
    json_request['params'] = details
    json_request['params'][mediatype + 'id'] = dbid

    json_result = pykodi.execute_jsonrpc(json_request)
    if not check_json_result(json_result, 'OK', json_request):
        log(json_result)

def get_base_json_request(method):
    return {'jsonrpc': '2.0', 'method': method, 'params': {}, 'id': 1}

def check_json_result(json_result, result_key, json_request):
    if 'error' in json_result:
        raise JSONException(json_request, json_result)

    return 'result' in json_result and (not result_key or result_key in json_result['result'])

class JSONException(Exception):
    def __init__(self, json_request, json_result):
        self.json_request = json_request
        self.json_result = json_result

        message = "There was an error with a JSON-RPC request.\nRequest: "
        message += pykodi.json_dumps(json_request, True)
        message += "\nResult: "
        message += pykodi.json_dumps(json_result, True)

        super(JSONException, self).__init__(message)
