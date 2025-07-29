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
    print(tracks["tracks"]) # example from main: {'type': 'track', 'total': 1, 'per_page': 20, 'order': 0, 'results': [{'id': 62728092, 'title': 'ПСД ебашит всех', 'available': True, 'artists': [{'id': 8762135, 'error': None, 'reason': None, 'name': 'ПОСЛЕДСТВИЕ СЫРНОГО ДЖО', 'cover': {'type': 'from-album-cover', 'uri': 'avatars.yandex.net/get-music-content/3318009/bebff23f.a.12615881-1/%%', 'items_uri': None, 'dir': None, 'version': None, 'custom': None, 'is_custom': None, 'copyright_name': None, 'copyright_cline': None, 'prefix': 'bebff23f.a.12615881-1', 'error': None}, 'various': False, 'composer': False, 'genres': [], 'og_image': None, 'op_image': None, 'no_pictures_from_search': None, 'counts': None, 'available': True, 'ratings': None, 'links': [], 'tickets_available': None, 'likes_count': None, 'popular_tracks': [], 'regions': None, 'decomposed': None, 'full_names': None, 'hand_made_description': None, 'description': None, 'countries': None, 'en_wikipedia_link': None, 'db_aliases': None, 'aliases': None, 'init_date': None, 'end_date': None, 'ya_money_id': None}], 'albums': [{'id': 9916593, 'error': None, 'title': '12 способов бросить жрать в маке', 'track_count': 12, 'artists': [{'id': 8762135, 'error': None, 'reason': None, 'name': 'ПОСЛЕДСТВИЕ СЫРНОГО ДЖО', 'cover': {'type': 'from-album-cover', 'uri': 'avatars.yandex.net/get-music-content/3318009/bebff23f.a.12615881-1/%%', 'items_uri': None, 'dir': None, 'version': None, 'custom': None, 'is_custom': None, 'copyright_name': None, 'copyright_cline': None, 'prefix': 'bebff23f.a.12615881-1', 'error': None}, 'various': False, 'composer': False, 'genres': [], 'og_image': None, 'op_image': None, 'no_pictures_from_search': None, 'counts': None, 'available': True, 'ratings': None, 'links': [], 'tickets_available': None, 'likes_count': None, 'popular_tracks': [], 'regions': None, 'decomposed': None, 'full_names': None, 'hand_made_description': None, 'description': None, 'countries': None, 'en_wikipedia_link': None, 'db_aliases': None, 'aliases': None, 'init_date': None, 'end_date': None, 'ya_money_id': None}], 'labels': ['ПОСЛЕДСТВИЕ СЫРНОГО ДЖО'], 'available': True, 'available_for_premium_users': True, 'version': None, 'cover_uri': 'avatars.yandex.net/get-music-content/2266607/a3fe31d1.a.9916593-1/%%', 'content_warning': 'explicit', 'original_release_year': None, 'genre': 'hardcore', 'text_color': None, 'short_description': None, 'description': None, 'is_premiere': None, 'is_banner': None, 'meta_type': 'music', 'storage_dir': 'a3fe31d1.a.9916593-1', 'og_image': 'avatars.yandex.net/get-music-content/2266607/a3fe31d1.a.9916593-1/%%', 'buy': None, 'recent': False, 'very_important': False, 'available_for_mobile': True, 'available_partially': False, 'bests': [62728090, 62728086, 62728083], 'duplicates': [], 'prerolls': None, 'volumes': None, 'year': 2020, 'release_date': '2020-02-14T00:00:00+03:00', 'type': None, 'track_position': {'volume': 1, 'index': 12}, 'regions': ['RUSSIA', 'RUSSIA_PREMIUM'], 'available_as_rbt': None, 'lyrics_available': None, 'remember_position': None, 'albums': [], 'duration_ms': None, 'explicit': None, 'start_date': None, 'likes_count': 130, 'deprecation': None, 'available_regions': [], 'available_for_options': ['bookmate']}], 'available_for_premium_users': True, 'lyrics_available': False, 'poetry_lover_matches': [], 'best': None, 'real_id': '62728092', 'og_image': 'avatars.yandex.net/get-music-content/2266607/a3fe31d1.a.9916593-1/%%', 'type': 'music', 'cover_uri': 'avatars.yandex.net/get-music-content/2266607/a3fe31d1.a.9916593-1/%%', 'major': {'id': 131, 'name': 'TUNECORE'}, 'duration_ms': 164670, 'storage_dir': '51327_109b74ca.36526310.1.609676', 'file_size': 0, 'substituted': None, 'matched_track': None, 'normalization': None, 'error': None, 'can_publish': None, 'state': None, 'desired_visibility': None, 'filename': None, 'user_info': None, 'meta_data': None, 'regions': ['RUSSIA', 'RUSSIA_PREMIUM'], 'available_as_rbt': True, 'content_warning': 'explicit', 'explicit': True, 'preview_duration_ms': 30000, 'available_full_without_permission': False, 'version': None, 'remember_position': False, 'background_video_uri': None, 'short_description': None, 'is_suitable_for_children': None, 'track_source': 'OWN', 'available_for_options': ['bookmate'], 'r128': {'i': 0.0, 'tp': 5.3}, 'lyrics_info': {'has_available_sync_lyrics': False, 'has_available_text_lyrics': False}, 'track_sharing_flag': 'COVER_ONLY', 'download_info': None}]}
    for track in tracks["tracks"]["results"]:
        print(track) # get "title" from track, also get ["cover_uri"] and "artists" joining all artists
        title = track["title"]
        uri = track["cover_uri"] # get via http(add http://),also there are %% at the and of link(example result is "avatars.yandex.net/get-music-content/2266607/a3fe31d1.a.9916593-1/%%"), replace it with required resolution, for example ready to get image link will be "http://avatars.yandex.net/get-music-content/2266607/a3fe31d1.a.9916593-1/100x100"
        artists = ", ".join([artist["name"] for artist in track["artists"]])
        print(title, uri, artists) # for example, for main search it will be "ПСД ебашит всех, avatars.yandex.net/get-music-content/2266607/a3fe31d1.a.9916593-1/%%, ПОСЛЕДСТВИЕ СЫРНОГО ДЖО"
        # format the URI to do an http link with required by telegram resolution, and return all formated tracks with lim 10. give title as main search result, artists names as description, cover as image preview





if __name__ == "__main__":
    search("псд ебашит всех")
    # download("6572738") # example track id, in prod extract it from url from "..trackId={id}.."
