import requests
import json
import datetime

from monthlify.core import read_config
from monthlify.core import BadRequestError


# finds a song in spotify by the artist
def find_track(auth, track, artist):
    conf = read_config()

    url = f'{conf.base_url}/search?q="{artist}"%20{track}&type=track'
    headers = {'Authorization': f'Bearer {auth.access_token}'}

    response = requests.get(url, headers=headers)

    results = json.loads(response.text)

    # find all important information
    result_track = (results["tracks"]["items"][0]["name"])
    result_artist = (results["tracks"]["items"][0]["artists"][0]["name"])
    result_uri = (results["tracks"]["items"][0]["uri"])

    # if the first result ain't it, it's probably the second result
    if artist != result_artist or track.lower() != result_track.lower():
        result_track = (results["tracks"]["items"][1]["name"])
        result_artist = (results["tracks"]["items"][1]["artists"][0]["name"])
        result_uri = (results["tracks"]["items"][1]["uri"])

    return result_track, result_artist, result_uri


# uses spotify api to directly find top 50 songs from ~past month
# return: list of uris
def find_top_tracks(auth):
    conf = read_config()

    url = f'{conf.base_url}/me/top/tracks'
    headers = {'Authorization': f'Bearer {auth.access_token}'}
    data = {'limit': 50,
            'time_range': 'short_term'}

    response = requests.get(url, headers=headers, params=data)

    if response.status_code != 200:
        print(response.status_code)
        raise BadRequestError()

    result = json.loads(response.text)

    tracks_list = []
    for i in range(50):
        uri = result["items"][i]["uri"]
        tracks_list.append(uri)

    return tracks_list


# makes an empty spotify playlist for the user
# returns the id of the newly made playlist
def create_playlist(auth, userid, playlist_name, desc):
    conf = read_config()

    url = f'{conf.base_url}/users/{userid}/playlists'
    headers = {'Authorization': f'Bearer {auth.access_token}',
               'Content-Type': 'application/json'}
    data = {'name': playlist_name,
            'public': False,
            'description': desc}

    response = requests.post(url, headers=headers, json=data)

    if response.status_code != 200 and response.status_code != 201:
        raise BadRequestError()

    content = json.loads(response.text)

    return content["id"]


# deletes a spotify playlist for the user (technically unfollows, not deletes)
def delete_playlist(auth, playlist_id):
    conf = read_config()

    url = f'{conf.base_url}/playlists/{playlist_id}/followers'
    headers = {'Authorization': f'Bearer {auth.access_token}'}

    response = requests.delete(url, headers=headers)

    if response.status_code != 200:
        raise BadRequestError()


# adds the specified tracks to the specified playlist
# params: playlistid--the spotify id of the playlist
#         tracks--list of track URIs
def populate_playlist(auth, playlistid, tracks):
    conf = read_config()

    url = f'{conf.base_url}/playlists/{playlistid}/tracks'
    headers = {'Authorization': f'Bearer {auth.access_token}'}
    data = {'uris': tracks}

    response = requests.post(url, headers=headers, json=data)

    content = json.loads(response.content.decode('utf-8'))

    if response.status_code != 201:
        error_description = content.get('error_description', None)
        raise BadRequestError(error_description)


# gets the audio features of the specified tracks from spotify
# params: tracks-- list of track IDs
def get_features(auth, tracks):

    conf = read_config()

    url = f'{conf.base_url}/audio-features'
    headers = {'Authorization': f'Bearer {auth.access_token}'}

    # tracks may have more than 100 items
    tracks_list = [tracks[i * 100:(i + 1) * 100] for i in range((len(tracks) + 99) // 100)]

    results = []

    for sub_list in tracks_list:
        params = {'ids': ','.join(sub_list)}

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            print(f'status code is: {response.status_code}')
            print(response.text)
            raise BadRequestError()

        results.append(json.loads(response.text))

    return results


# scrapes spotify data for up to 50 most recently played tracks
# params: last_scraped_ms--unix timestamp in ms since epoch;
#                          only data after this time will be scraped
# return: name of the newly created raw data file
def get_recently_played(auth, last_scraped_ms=0):
    conf = read_config()

    url = f'{conf.base_url}/me/player/recently-played'
    headers = {'Authorization': f'Bearer {auth.access_token}'}

    print(f'last scraped ms: {last_scraped_ms}')
    params = {'limit': 50,
              'after': last_scraped_ms}

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print(response.status_code)
        print(response.text)
        raise BadRequestError()

    now = datetime.datetime.now() - datetime.timedelta(hours=-4)

    with open(f'./play_log/raw/{now}.json', mode='w', encoding='utf-8') as file:
        file.write(response.text)
        print("raw file written")

    return f'{now}.json'


def get_all_playlists(auth):
    conf = read_config()

    url = f'{conf.base_url}/me/playlists'
    headers = {'Authorization': f'Bearer {auth.access_token}'}

    # max 50 playlists
    params = {'limit': 50}

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print(response.status_code)
        print(response.text)
        raise BadRequestError()

    with open(f'./monthlify/data/playlists.json', mode='w', encoding='utf-8') as file:
        file.write(response.text)

    results = json.loads(response.text)

    return results


def get_tracks_from_playlist(auth, playlist_id, offset=0):
    conf = read_config()

    url = f'{conf.base_url}/playlists/{playlist_id}/tracks'
    headers = {'Authorization': f'Bearer {auth.access_token}'}
    params = {'offset': offset}

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print(response.status_code)
        print(response.text)
        raise BadRequestError()

    results = json.loads(response.text)

    return results
