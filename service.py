import json
import xbmc
import xbmcaddon
from datetime import timedelta

from lib import quickjson
from lib.pykodi import log, datetime_now, datetime_strptime, get_kodi_version

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
        waittime = 5
        while not self.waitForAbort(waittime):
            if self.paused:
                self.pausedtime += waittime
        log('Service stopped')

    def onNotification(self, sender, method, data):
        if method not in ('Player.OnPlay', 'Player.OnStop', 'Player.OnPause', 'VideoLibrary.OnUpdate'):
            return
        data = json.loads(data)

        if is_data_onplay_bugged(data, method):
            data['item']['id'], data['item']['type'] = hack_onplay_databits()

        if 'item' not in data or 'id' not in data['item'] or data.get('transaction') or \
                data['item']['type'] not in ('movie', 'episode') or data['item']['id'] == -1:
            log("Not watching this item")
            return
        else:
            data_id = data['item']['id']
            data_type = data['item']['type']

        if method == 'Player.OnPlay':
            if not self.paused:
                self._add_item_to_watchlist(data_type, data_id)
                self.pausedtime = 0
            self.paused = False
        elif method == 'Player.OnPause':
            self.paused = True
        elif method == 'Player.OnStop':
            self.paused = False
            # sometimes OnUpdate isn't received or is incorrect, so gotta check after OnStop
            # OnStop can fire before the library is updated, so delay check
            self.delay = 2000
            self._check_item_against_watchlist(data)
        elif method == 'VideoLibrary.OnUpdate':
            if not self.delay:
                self._check_item_against_watchlist(data)
            else:
                self.delay = 0

    def _add_item_to_watchlist(self, data_type, data_id):
        if data_type == 'episode':
            json_result = quickjson.get_episode_details(data_id)
        elif data_type == 'movie':
            json_result = quickjson.get_movie_details(data_id)

        new_item = {'type': data_type, 'id': data_id, 'start time': datetime_now(),
            'DB last played': json_result['lastplayed']}
        log(new_item)
        self.watchlist.append(new_item)

    checktick = 100
    def _check_item_against_watchlist(self, data):
        while self.delay > 0:
            xbmc.sleep(self.checktick)
            self.delay -= self.checktick
            if self.abortRequested():
                return
        matching = next((item for item in self.watchlist if matches(item, data['item'])), None)
        if matching:
            self.watchlist = [item for item in self.watchlist if not matches(item, data['item'])]
            if data.get('end'):
                # The video was played through to the end, no need to revert lastplayed
                log("Video watched to end, not reverting")
            elif matching['type'] == 'episode':
                json_result = quickjson.get_episode_details(data['item']['id'])
                if json_result['lastplayed'] != matching['DB last played'] and \
                        self.should_revert_lastplayed(matching['start time'], json_result['lastplayed']):
                    quickjson.set_episode_details(matching['id'], lastplayed=matching['DB last played'])
                    log("Reverted episode '{0}' last played timestamp".format(json_result['title']))
                else:
                    log("Not reverting episode '{0}' last played timestamp".format(json_result['title']))
            elif matching['type'] == 'movie':
                json_result = quickjson.get_movie_details(data['item']['id'])
                if json_result['lastplayed'] != matching['DB last played'] and \
                        self.should_revert_lastplayed(matching['start time'], json_result['lastplayed']):
                    quickjson.set_movie_details(matching['id'], lastplayed=matching['DB last played'])
                    log("Reverted movie '{0}' last played timestamp.".format(json_result['title']))
                else:
                    log("Not reverting movie '{0}' last played timestamp".format(json_result['title']))
        else:
            log("Item not in watch list")
        self.delay = False

    def should_revert_lastplayed(self, start_time, newlastplayed_string):
        lastplayed_time = datetime_strptime(newlastplayed_string, '%Y-%m-%d %H:%M:%S')
        try:
            update_after = float(xbmcaddon.Addon().getSetting(SETTING_UPDATE_AFTER)) * 60
        except ValueError:
            update_after = 120

        compareseconds = update_after + self.pausedtime
        return lastplayed_time < start_time + timedelta(seconds=compareseconds)

def matches(item, dataitem):
    return item['type'] == dataitem['type'] and item['id'] == dataitem['id']

def is_data_onplay_bugged(data, method):
    # WARN: OnUpdate for playcount/lastplayed after playing is also bugged and spits out {"id":-1,"type":""}
    return 'item' in data and 'id' not in data['item'] and data['item'].get('type') == 'movie' and \
        data['item'].get('title') == '' and get_kodi_version() >= 17 and method == 'Player.OnPlay'

def hack_onplay_databits():
    # HACK: Workaround for Kodi 17 bug, not including the correct info in the notification when played
    #  from home window or other non-media windows. http://trac.kodi.tv/ticket/17270

    # VideoInfoTag can be incorrect immediately after the notification as well, keep trying
    data_id = xbmc.Player().getVideoInfoTag().getDbId()
    count = 0
    while (not data_id or data_id == -1) and count < 4:
        xbmc.sleep(500)
        data_id = xbmc.Player().getVideoInfoTag().getDbId()
        count += 1
    if not data_id or data_id == -1:
        return -1, ""
    return data_id, xbmc.Player().getVideoInfoTag().getMediaType()

if __name__ == '__main__':
    service = TweakLastPlayedService()
    try:
        service.run()
    finally:
        del service
