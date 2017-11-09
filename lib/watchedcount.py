import xbmc

from lib.libs.pykodi import datetime_now, datetime_strptime
from lib.libs import quickjson

def add_one(dbid, mediatype):
    mediaitem = quickjson.get_details(dbid, mediatype)
    playcount = mediaitem['playcount'] + 1
    lastplayed = datetime_now()
    quickjson.set_item_details(dbid, mediatype, playcount=playcount, lastplayed=str(lastplayed).split('.')[0])
    xbmc.executebuiltin('Container.Refresh')

def remove_one(dbid, mediatype):
    mediaitem = quickjson.get_details(dbid, mediatype)
    lastplayed = datetime_strptime(mediaitem['lastplayed'], '%Y-%m-%d %H:%M:%S')
    dateadded = datetime_strptime(mediaitem['dateadded'], '%Y-%m-%d %H:%M:%S')

    newplaycount = mediaitem['playcount'] - 1
    newlastplayed = lastplayed - (lastplayed - dateadded) / newplaycount
    quickjson.set_item_details(dbid, mediatype, playcount=newplaycount, lastplayed=str(newlastplayed).split('.')[0])
    xbmc.executebuiltin('Container.Refresh')

def clear_resume(dbid, mediatype):
    quickjson.set_item_details(dbid, mediatype, resume={'position': 0, 'total': 0})
    xbmc.executebuiltin('Container.Refresh')
