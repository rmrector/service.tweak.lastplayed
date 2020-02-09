import sys

from lib import watchedcount

def main(mode):
    mediatype = sys.listitem.getVideoInfoTag().getMediaType()
    dbid = sys.listitem.getVideoInfoTag().getDbId()
    if not dbid or not mediatype:
        return

    if mode == 'add':
        watchedcount.add_one(dbid, mediatype)
    elif mode == 'remove':
        watchedcount.remove_one(dbid, mediatype)

if __name__ == '__main__':
    main('add')
