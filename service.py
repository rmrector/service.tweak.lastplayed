import xbmc
import xbmcaddon
from datetime import timedelta

from lib.libs import quickjson
from lib.libs.pykodi import log, datetime_now, datetime_strptime, get_kodi_version, json

class TweakLastPlayedService(xbmc.Monitor):
    def __init__(self):
        super(TweakLastPlayedService, self).__init__()
        self.watchlist = []
        self.delay = 0
        self.paused = False
        self.pausedtime = 0
        self.update_after = 0

    def run(self):
        waittime = 5
        while not self.waitForAbort(waittime):
            if self.paused:
                self.pausedtime += waittime

    def onNotification(self, sender, method, data):
        if method not in ('Player.OnPlay', 'Player.OnStop', 'Player.OnPause', 'VideoLibrary.OnUpdate'):
            return
        if not self.update_after:
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
            self.delay = 1000
            self._check_item_against_watchlist(data)
        elif method == 'VideoLibrary.OnUpdate':
            if not self.delay:
                self._check_item_against_watchlist(data)
            else:
                self.delay = 0

    def _add_item_to_watchlist(self, data_type, data_id):
        json_result = quickjson.get_details(data_id, data_type)

        new_item = {'type': data_type, 'id': data_id, 'start time': datetime_now(),
            'DB last played': json_result['lastplayed']}
        self.watchlist.append(new_item)

    checktick = 100
    def _check_item_against_watchlist(self, data):
        while self.delay > 0:
            xbmc.sleep(self.checktick)
            self.delay -= self.checktick
            if self.abortRequested():
                return
        self.delay = False
        matching = next((item for item in self.watchlist if matches(item, data['item'])), None)
        if not matching:
            log("Item not in watch list")
            return
        self.watchlist = [item for item in self.watchlist if not matches(item, data['item'])]
        if data.get('end'):
            log("Video watched to end, not reverting")
            return
        json_result = quickjson.get_details(data['item']['id'], matching['type'])
        if not self.should_revert_lastplayed(matching['start time'], json_result['lastplayed']):
            log("Not reverting  {0} '{1}' last played timestamp".format(matching['type'], json_result['title']))
            return

        quickjson.set_details(matching['id'], matching['type'], lastplayed=matching['DB last played'])
        log("Reverted {0} '{1}' last played timestamp".format(matching['type'], json_result['title']))

    def should_revert_lastplayed(self, start_time, newlastplayed_string):
        if start_time == newlastplayed_string:
            return False
        lastplayed_time = datetime_strptime(newlastplayed_string, '%Y-%m-%d %H:%M:%S')
        compareseconds = self.update_after + self.pausedtime
        return lastplayed_time < start_time + timedelta(seconds=compareseconds)

    def onSettingsChanged(self):
        try:
            self.update_after = float(xbmcaddon.Addon().getSetting('update_after')) * 60
        except ValueError:
            xbmcaddon.Addon().setSetting('update_after', "2")
            self.update_after = 120

def matches(item, dataitem):
    return item['type'] == dataitem['type'] and item['id'] == dataitem['id']

def is_data_onplay_bugged(data, method):
    # WARN: OnUpdate for playcount/lastplayed after playing can also be bugged and spits out {"id":-1,"type":""}
    return 'item' in data and 'id' not in data['item'] and data['item'].get('type') == 'movie' and \
        data['item'].get('title') == '' and method == 'Player.OnPlay' and get_kodi_version() >= 17

def hack_onplay_databits():
    # HACK: Workaround for Kodi 17 bug, not including the correct info in the notification when played
    #  from home window or other non-media windows. http://trac.kodi.tv/ticket/17270

    # VideoInfoTag can be incorrect immediately after the notification as well, keep trying
    count = 0
    mediatype = xbmc.Player().getVideoInfoTag().getMediaType()
    while not mediatype and count < 20:
        xbmc.sleep(100)
        mediatype = xbmc.Player().getVideoInfoTag().getMediaType()
        count += 1
    if not mediatype:
        return -1, ""
    return xbmc.Player().getVideoInfoTag().getDbId(), mediatype

if __name__ == '__main__':
    log('Service started', xbmc.LOGINFO)
    TweakLastPlayedService().run()
    log('Service stopped', xbmc.LOGINFO)
