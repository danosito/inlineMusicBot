#file to download from yandex music

from yandex_music import Client


def download(link):
    clientForUser = Client("<token>") # create a /token for setting into sqlite3 db like userid-yandexToken-(if required)spotifyToken
    clientForUser.init()
    track = clientForUser.tracks([link])[0]
    print(track)
    track.download("test.mp3")


def search(query):
    clientForUser = Client() # load from token db, but can be searched without loading token UwU
    clientForUser.init()
    tracks = clientForUser.search(query)
    print(tracks["tracks"])
    for track in tracks["tracks"]["results"]:
        print(track) # get "title" from track, also get ["cover_uri"] and "artists" joining all artists, and id to download'
        trackid = track["id"]
        title = track["title"]
        uri = track["cover_uri"] # get via http(add http://),also there are %% at the and of link(example result is "avatars.yandex.net/get-music-content/2266607/a3fe31d1.a.9916593-1/%%"), replace it with required resolution, for example ready to get image link will be "http://avatars.yandex.net/get-music-content/2266607/a3fe31d1.a.9916593-1/100x100"
        artists = ", ".join([artist["name"] for artist in track["artists"]])
        print(title, uri, artists, trackid) # for example, for main search it will be "ПСД ебашит всех, avatars.yandex.net/get-music-content/2266607/a3fe31d1.a.9916593-1/%%, ПОСЛЕДСТВИЕ СЫРНОГО ДЖО"
        # format the URI to do an http link with required by telegram resolution, and return all formated tracks with lim 10. give title as main search result, artists names as description, cover as image preview, and trackid as hidden data to download the track





if __name__ == "__main__":
    search("псд ебашит всех")
    # download("6572738") # example track id, in prod extract it from url from "..trackId={id}.."
