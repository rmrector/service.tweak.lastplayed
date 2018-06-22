import xbmc
import xbmcaddon
from datetime import timedelta

from lib.libs import pykodi, quickjson
from lib.libs.pykodi import log, get_kodi_version

class TweakLastPlayedService(xbmc.Monitor):
    def __init__(self):
        super(TweakLastPlayedService, self).__init__()
        self.waittime = 2
        self.signal = None

        self.watchlist = []
        self.checklist = []
        self.paused = False
        self.pausedtime = 0
        self.update_after = 0
        self.load_settings()

    def run(self):
        while not self.waitForAbort(self.waittime):
            if self.paused:
                self.pausedtime += self.waittime
            elif self.signal:
                if self.signal == 'check':
                    self.signal = 'check_really'
                elif self.signal == 'check_really':
                    for dataitem in self.checklist:
                        if 'end' in dataitem:
                            self.check_data(dataitem)
                    self.checklist = []
                    self.signal = None

    def onNotification(self, sender, method, data):
        if method not in ('Player.OnPlay', 'Player.OnStop', 'Player.OnPause', 'VideoLibrary.OnUpdate'):
            return
        if not self.update_after:
            return
        data = get_notificationdata(data, method)

        if 'item' not in data or 'id' not in data['item'] or data.get('transaction') or \
                data['item']['type'] not in ('movie', 'episode') or data['item']['id'] == -1:
            log("Not watching this item")
            return
        else:
            data_id = data['item']['id']
            data_type = data['item']['type']

        if method == 'Player.OnPlay':
            if not self.paused:
                self.add_item_to_watchlist(data_type, data_id)
                self.pausedtime = 0
            self.paused = False
        elif method == 'Player.OnPause':
            self.paused = True
        elif method == 'Player.OnStop':
            self.paused = False
            dataitem = data['item']
            dataitem['end'] = data.get('end', False)
            self.add_data_to_checklist(dataitem)
        elif method == 'VideoLibrary.OnUpdate':
            dataitem = data['item']
            dataitem['updated'] = True
            self.add_data_to_checklist(dataitem)

    def add_item_to_watchlist(self, data_type, data_id):
        json_result = quickjson.get_details(data_id, data_type)

        new_item = {'type': data_type, 'id': data_id, 'start time': pykodi.datetime_now(),
            'DB last played': json_result['lastplayed'], 'DB resume': json_result['resume']}
        self.watchlist.append(new_item)

    def add_data_to_checklist(self, dataitem):
        prevdata = next(iter_matching(dataitem, self.checklist), None)
        if prevdata:
            for key in ('updated', 'end'):
                if key in prevdata and key not in dataitem:
                    dataitem[key] = prevdata[key]
            self.checklist.remove(prevdata)
        self.checklist.append(dataitem)
        self.signal = 'check'

    def check_data(self, dataitem):
        matching = next(iter_matching(dataitem, self.watchlist), None)
        if not matching:
            log("Item not in watch list")
            return
        self.watchlist = list(iter_matching(dataitem, self.watchlist, True))
        if dataitem['end']:
            log("Video watched to end, not reverting")
            return
        json_result = quickjson.get_details(dataitem['id'], matching['type'])
        if not self.should_revert_lastplayed(matching['start time'], json_result['lastplayed']):
            log("Not reverting  {0} '{1}' last played timestamp".format(matching['type'], json_result['title']))
            return

        quickjson.set_item_details(matching['id'], matching['type'], lastplayed=matching['DB last played'],
            resume=matching['DB resume'])
        log("Reverted {0} '{1}' last played timestamp".format(matching['type'], json_result['title']))

    def should_revert_lastplayed(self, start_time, newlastplayed_string):
        if start_time == newlastplayed_string:
            return False
        lastplayed_time = pykodi.datetime_strptime(newlastplayed_string, '%Y-%m-%d %H:%M:%S')
        compareseconds = self.update_after + self.pausedtime
        return lastplayed_time < start_time + timedelta(seconds=compareseconds)

    def onSettingsChanged(self):
        self.load_settings()

    def load_settings(self):
        try:
            self.update_after = float(xbmcaddon.Addon().getSetting('update_after')) * 60
        except ValueError:
            xbmcaddon.Addon().setSetting('update_after', "2")
            self.update_after = 120

def iter_matching(dataitem, thelist, reversematch=False):
    for item in thelist:
        if (item['type'] == dataitem['type'] and item['id'] == dataitem['id']) ^ reversematch:
            yield item

def get_notificationdata(data, method):
    data = pykodi.json_loads(data)
    if is_data_onplay_bugged(data, method):
        data['item']['id'], data['item']['type'] = hack_onplay_databits()
    return data

def is_data_onplay_bugged(data, method):
    return 'item' in data and 'id' not in data['item'] and data['item'].get('type') == 'movie' and \
        data['item'].get('title') == '' and method == 'Player.OnPlay' and get_kodi_version() in (17, 18)
    # fixed between Kodi 18 alpha1 and alpha2

def hack_onplay_databits():
    # HACK: Workaround for Kodi 17 bug, not including the correct info in the notification when played
    #  from home window or other non-media windows. http://trac.kodi.tv/ticket/17270

    # VideoInfoTag can be incorrect immediately after the notification as well, keep trying
    count = 0
    if not xbmc.Player().isPlayingVideo():
        return -1, ""
    mediatype = xbmc.Player().getVideoInfoTag().getMediaType()
    while not mediatype and count < 10:
        xbmc.sleep(200)
        if not xbmc.Player().isPlayingVideo():
            return -1, ""
        mediatype = xbmc.Player().getVideoInfoTag().getMediaType()
        count += 1
    if not mediatype:
        return -1, ""
    return xbmc.Player().getVideoInfoTag().getDbId(), mediatype

if __name__ == '__main__':
    log('Service started', xbmc.LOGINFO)
    TweakLastPlayedService().run()
    log('Service stopped', xbmc.LOGINFO)
