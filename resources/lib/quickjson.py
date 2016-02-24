import pykodi
from pykodi import log

default_properties = ['title', 'lastplayed']

def get_movie_details(movie_id, properties=None):
    json_request = get_base_json_request('VideoLibrary.GetMovieDetails')
    json_request['params']['movieid'] = movie_id
    json_request['params']['properties'] = properties if properties else default_properties

    json_result = pykodi.execute_jsonrpc(json_request)

    if _check_json_result(json_result, 'moviedetails', json_request):
        return json_result['result']['moviedetails']

def get_episode_details(episode_id, properties=None):
    json_request = get_base_json_request('VideoLibrary.GetEpisodeDetails')
    json_request['params']['episodeid'] = episode_id
    json_request['params']['properties'] = properties if properties else default_properties

    json_result = pykodi.execute_jsonrpc(json_request)

    if _check_json_result(json_result, 'episodedetails', json_request):
        return json_result['result']['episodedetails']

def set_episode_details(episode_id, **episode_details):
    json_request = get_base_json_request('VideoLibrary.SetEpisodeDetails')
    json_request['params'] = episode_details
    json_request['params']['episodeid'] = episode_id

    json_result = pykodi.execute_jsonrpc(json_request)
    if not _check_json_result(json_result, 'OK', json_request):
        log(json_result)

def set_movie_details(movie_id, **movie_details):
    json_request = get_base_json_request('VideoLibrary.SetMovieDetails')
    json_request['params'] = movie_details
    json_request['params']['movieid'] = movie_id

    json_result = pykodi.execute_jsonrpc(json_request)
    if not _check_json_result(json_result, 'OK', json_request):
        log(json_result)

def get_base_json_request(method):
    return {'jsonrpc': '2.0', 'method': method, 'params': {}, 'id': 1}

def _check_json_result(json_result, result_key, json_request):
    if 'result' in json_result and result_key in json_result['result']:
        return True
    elif 'error' in json_result:
        log("JSON-RPC query error.")
        log(json_request)
        log(json_result)
        return False
    else:
        return False
