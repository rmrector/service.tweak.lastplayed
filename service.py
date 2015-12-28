import json
import xbmc
from datetime import datetime, timedelta

import os, sys, xbmcaddon
addon = xbmcaddon.Addon()
resourcelibs = xbmc.translatePath(addon.getAddonInfo('path')).decode('utf-8')
resourcelibs = os.path.join(resourcelibs, u'resources', u'lib')
sys.path.append(resourcelibs)

import quickjson
import pykodi
from pykodi import log

SETTING_UPDATE_AFTER = 'update_after'

class KodiMonitor(xbmc.Monitor):
    watchlist = []
    def __init__(self):
        xbmc.Monitor.__init__(self)
        self.delay = False
        self.paused = False
        self.pausedtime = 0

    def run(self):
        log('Service started')
        waittime = 10
        while not self.waitForAbort(waittime):
            if self.paused:
                self.pausedtime += waittime
        log('Service stopped')

    def onNotification(self, sender, method, data):
        data = json.loads(data)
        if method not in ('Player.OnPlay', 'Player.OnStop', 'Player.OnPause', 'VideoLibrary.OnUpdate'):
            return
        if 'item' not in data or 'id' not in data['item'] or data['item']['type'] not in ['movie', 'episode']:
            return # only care about library videos that are likely to be longer than a few minutes anyway

        if method == 'Player.OnPlay':
            if not self.paused:
                self._add_item_to_watchlist(data)
                self.pausedtime = 0
            self.paused = False
        elif method == 'Player.OnPause':
            self.paused = True
        elif method == 'Player.OnStop':
            self.paused = False
            self.delay = datetime.now() + timedelta(seconds=2)
            self._check_item_against_watchlist(data)
        elif method == 'VideoLibrary.OnUpdate':
            if not self.delay:
                self._check_item_against_watchlist(data)
            else:
                self.delay = False

    def _add_item_to_watchlist(self, data):
        if data['item']['type'] == 'episode':
            json_result = quickjson.get_episode_details(data['item']['id'])
        elif data['item']['type'] == 'movie':
            json_result = quickjson.get_movie_details(data['item']['id'])

        new_item = {'type': data['item']['type'], 'id': data['item']['id'], 'start time': datetime.now(), 'DB last played': json_result['lastplayed']}
        self.watchlist.append(new_item)

    def _check_item_against_watchlist(self, data):
        while self.delay and datetime.now() < self.delay:
            xbmc.sleep(100)
        matching = [item for item in self.watchlist if item['type'] == data['item']['type'] and item['id'] == data['item']['id']]
        if matching:
            matching = matching[0]
            self.watchlist = [item for item in self.watchlist if not (item['type'] == data['item']['type'] and item['id'] == data['item']['id'])]
            if matching['type'] == 'episode':
                json_result = quickjson.get_episode_details(data['item']['id'])
                if self.should_revert_lastplayed(matching['start time'], json_result['lastplayed']) and json_result['lastplayed'] != matching['DB last played']:
                    quickjson.set_episode_details(matching['id'], lastplayed=matching['DB last played'])
            elif matching['type'] == 'movie':
                json_result = quickjson.get_movie_details(data['item']['id'])
                if self.should_revert_lastplayed(matching['start time'], json_result['lastplayed']) and json_result['lastplayed'] != matching['DB last played']:
                    quickjson.set_movie_details(matching['id'], lastplayed=matching['DB last played'])
        self.delay = False

    def should_revert_lastplayed(self, start_time, lastplayed_string):
        lastplayed_time = datetime.strptime(lastplayed_string, '%Y-%m-%d %H:%M:%S')
        try:
            update_after = float(addon.getSetting(SETTING_UPDATE_AFTER)) * 60
        except ValueError:
            update_after = 120

        compareseconds = update_after + self.pausedtime
        return lastplayed_time < start_time + timedelta(seconds=compareseconds)

if __name__ == '__main__':
    if pykodi.first_datetime():
        monitor = KodiMonitor()
        monitor.run()
