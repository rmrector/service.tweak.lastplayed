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

class TweakLastPlayedService(xbmc.Monitor):
    def __init__(self):
        super(TweakLastPlayedService, self).__init__()
        self.watchlist = []
        self.delay = 0
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
        if method not in ('Player.OnPlay', 'Player.OnStop', 'Player.OnPause', 'VideoLibrary.OnUpdate'):
            return
        data = json.loads(data)
        if 'item' not in data or 'id' not in data['item'] or data['item']['type'] not in ('movie', 'episode'):
            return # Keep it simple by tracking only library videos that are likely to be longer than a few minutes anyway

        if method == 'Player.OnPlay':
            if not self.paused:
                self._add_item_to_watchlist(data)
                self.pausedtime = 0
            self.paused = False
        elif method == 'Player.OnPause':
            self.paused = True
        elif method == 'Player.OnStop':
            self.paused = False
            # OnStop is fired before the library is updated, so delay check
            # OnUpdate is probably going to show up very soon, then the check can proceed
            self.delay = 2000
            self._check_item_against_watchlist(data)
        elif method == 'VideoLibrary.OnUpdate':
            if not self.delay:
                self._check_item_against_watchlist(data)
            else:
                self.delay = 0

    def _add_item_to_watchlist(self, data):
        if data['item']['type'] == 'episode':
            json_result = quickjson.get_episode_details(data['item']['id'])
        elif data['item']['type'] == 'movie':
            json_result = quickjson.get_movie_details(data['item']['id'])

        new_item = {'type': data['item']['type'], 'id': data['item']['id'], 'start time': datetime.now(), 'DB last played': json_result['lastplayed']}
        self.watchlist.append(new_item)

    checktick = 100
    def _check_item_against_watchlist(self, data):
        while self.delay > 0:
            xbmc.sleep(self.checktick)
            self.delay -= self.checktick
        matching = [item for item in self.watchlist if matches(item, data['item'])]
        if matching:
            matching = matching[0]
            self.watchlist = [item for item in self.watchlist if not matches(item, data['item'])]
            if 'end' in data and data['end']:
                pass # The video was played through to the end, no need to revert lastplayed
            elif matching['type'] == 'episode':
                json_result = quickjson.get_episode_details(data['item']['id'])
                if json_result['lastplayed'] != matching['DB last played'] and self.should_revert_lastplayed(matching['start time'], json_result['lastplayed']):
                    quickjson.set_episode_details(matching['id'], lastplayed=matching['DB last played'])
                    log("Reverted episode '%s' last played timestamp." % json_result['title'])
            elif matching['type'] == 'movie':
                json_result = quickjson.get_movie_details(data['item']['id'])
                if json_result['lastplayed'] != matching['DB last played'] and self.should_revert_lastplayed(matching['start time'], json_result['lastplayed']):
                    quickjson.set_movie_details(matching['id'], lastplayed=matching['DB last played'])
                    log("Reverted movie '%s' last played timestamp." % json_result['title'])
        self.delay = False

    def should_revert_lastplayed(self, start_time, newlastplayed_string):
        lastplayed_time = datetime.strptime(newlastplayed_string, '%Y-%m-%d %H:%M:%S')
        try:
            update_after = float(addon.getSetting(SETTING_UPDATE_AFTER)) * 60
        except ValueError:
            update_after = 120

        compareseconds = update_after + self.pausedtime
        return lastplayed_time < start_time + timedelta(seconds=compareseconds)

def matches(item, dataitem):
    return item['type'] == dataitem['type'] and item['id'] == dataitem['id']

if __name__ == '__main__':
    if pykodi.first_datetime():
        service = TweakLastPlayedService()
        try:
            service.run()
        finally:
            del service
