from __future__ import unicode_literals

import json
import xbmc
from datetime import datetime, timedelta

from devhelper.pykodi import log
from devhelper import quickjson

seconds_to_ignore = 60

class KodiMonitor(xbmc.Monitor):
    watchlist = []

    def __init__(self):
        xbmc.Monitor.__init__(self)

        log('Started')
        while not self.waitForAbort(1):
            pass # Keep alive to receive onNotification
        
        # Received the abort command
        log('Stopped')

    def onNotification(self, sender, method, data):
        data = json.loads(data)
        if method == 'Player.OnPlay':
            self._add_item_to_watchlist(data)
        elif method == 'VideoLibrary.OnUpdate':
            self._check_item_against_watchlist(data)

    def _add_item_to_watchlist(self, data):
        if data['item']['type'] == 'episode':
            json_result = quickjson.get_episode_details(data['item']['id'])
        elif data['item']['type'] == 'movie':
            json_result = quickjson.get_movie_details(data['item']['id'])
        else:
            log("Don't know what to do with item type %s, so I can't fix its lastplayed timestamp later" % data['item']['type'])
            return
        new_item = {'type': data['item']['type'], 'id': data['item']['id'], 'start time': _current_time(), 'DB last played': json_result['lastplayed']}
        self.watchlist.append(new_item)

    def _check_item_against_watchlist(self, data):
        matching = [item for item in self.watchlist if item['type'] == data['item']['type'] and item['id'] == data['item']['id']]
        if matching:
            matching = matching[0]
            self.watchlist = [item for item in self.watchlist
                if not (item['type'] == data['item']['type'] and item['id'] == data['item']['id'])]
            if matching['type'] == 'episode':
                json_result = quickjson.get_episode_details(data['item']['id'])
                if _should_revert_lastplayed(matching['start time'], json_result['lastplayed']):
                    quickjson.set_episode_details(matching['id'], lastplayed=matching['DB last played'])
            elif matching['type'] == 'movie':
                json_result = quickjson.get_movie_details(data['item']['id'])
                if _should_revert_lastplayed(matching['start time'], json_result['lastplayed']):
                    quickjson.set_movie_details(matching['id'], lastplayed=matching['DB last played'])
            else:
                log("Don't know what to do with item type %s, so I can't fix its lastplayed timestamp" % matching['type'])

def _current_time():
    try:
        return datetime.now()
    except ImportError:
        xbmc.sleep(50)
        return _current_time()

def _should_revert_lastplayed(start_time, lastplayed_string):
    lastplayed_time = datetime.strptime(lastplayed_string, '%Y-%m-%d %H:%M:%S')
    return lastplayed_time < start_time + timedelta(seconds=seconds_to_ignore)

if __name__ == '__main__':
    KodiMonitor()
