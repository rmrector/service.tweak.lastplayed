import json
import xbmc
from datetime import datetime, timedelta

import os, sys, xbmcaddon
addon = xbmcaddon.Addon()
resourcelibs = xbmc.translatePath(addon.getAddonInfo('path')).decode('utf-8')
resourcelibs = os.path.join(resourcelibs, u'resources', u'lib')
sys.path.append(resourcelibs)

seconds_to_ignore = 120
import quickjson
import pykodi
from pykodi import log

class KodiMonitor(xbmc.Monitor):
    watchlist = []
    def __init__(self):
        xbmc.Monitor.__init__(self)

    def onNotification(self, sender, method, data):
        data = json.loads(data)
        if method not in ['Player.OnPlay', 'VideoLibrary.OnUpdate']: # watch for OnUpdate because the update may happen later than OnStop
            return
        if 'item' not in data or 'id' not in data['item'] or data['item']['type'] not in ['movie', 'episode']:
            return # only care about library videos that are likely to be longer than a few minutes anyway

        if method == 'Player.OnPlay':
            self._add_item_to_watchlist(data)
        elif method == 'VideoLibrary.OnUpdate':
            self._check_item_against_watchlist(data)

    def _add_item_to_watchlist(self, data):
        if data['item']['type'] == 'episode':
            json_result = quickjson.get_episode_details(data['item']['id'])
        elif data['item']['type'] == 'movie':
            json_result = quickjson.get_movie_details(data['item']['id'])

        new_item = {'type': data['item']['type'], 'id': data['item']['id'], 'start time': datetime.now(), 'DB last played': json_result['lastplayed']}
        self.watchlist.append(new_item)

    def _check_item_against_watchlist(self, data):
        matching = [item for item in self.watchlist if item['type'] == data['item']['type'] and item['id'] == data['item']['id']]
        if matching:
            matching = matching[0]
            self.watchlist = [item for item in self.watchlist if not (item['type'] == data['item']['type'] and item['id'] == data['item']['id'])]
            if matching['type'] == 'episode':
                json_result = quickjson.get_episode_details(data['item']['id'])
                if _should_revert_lastplayed(matching['start time'], json_result['lastplayed']):
                    quickjson.set_episode_details(matching['id'], lastplayed=matching['DB last played'])
            elif matching['type'] == 'movie':
                json_result = quickjson.get_movie_details(data['item']['id'])
                if _should_revert_lastplayed(matching['start time'], json_result['lastplayed']):
                    quickjson.set_movie_details(matching['id'], lastplayed=matching['DB last played'])

def _should_revert_lastplayed(start_time, lastplayed_string):
    lastplayed_time = datetime.strptime(lastplayed_string)
    return lastplayed_time < start_time + timedelta(seconds=seconds_to_ignore)

if __name__ == '__main__':
    if pykodi.first_datetime():
        monitor = KodiMonitor()
        log('Started')
        monitor.waitForAbort()

        log('Stopped')

