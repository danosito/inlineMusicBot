#file to download from yandex music

from yandex_music import Client


def download(link):
    clientForUser = Client("<token>") # create a /token for setting into sqlite3 db like userid-yandexToken-(if required)spotifyToken
    clientForUser.init()
    track = clientForUser.tracks([link])[0]
    print(track)
    track.download("test.mp3")

if __name__ == "__main__":
    download("6572738") # example track id, in prod extract it from url from "..trackId={id}.."
