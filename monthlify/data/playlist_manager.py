import json

from monthlify.auth import authenticate
from monthlify.core import read_config
from monthlify.core import BadRequestError
import monthlify.data.spotify_api as spotify_api


class PlaylistManager:

    def __init__(self):
        self._conf = read_config()
        self._auth = authenticate(self._conf)

    def find_track(self, track, artist):
        result_track, result_artist, result_uri = spotify_api.find_track(self._auth, track, artist)

        if artist != result_artist or track.lower() != result_track.lower():
            print(f'{result_track} by {result_artist} instead of {track} by {artist}')

        return result_uri

    # prepares a list of tracks to be made into a playlist.
    # params: filename--name of an optional json array file with (song, artist) lists as values.
    #                   if a file is not provided, it will use the spotify api to grab data.
    # return: a list of the URIs
    def prepare_tracks(self, filename=""):
        if filename:
            with open(filename, mode='r', encoding='utf-8') as file:
                contents = json.load(file)
                tracks_list = []
                for item in contents:
                    track = item[0]
                    artist = item[1]
                    tracks_list.append(self.find_track(track, artist))
                return tracks_list
        else:
            return spotify_api.find_top_tracks(self._auth)

    # creates and populates a playlist with specified tracks
    # params: userid--the user's spotify id
    #         name--the name of the playlist
    #         tracks--list of track URIs for the playlist
    def prepare_playlist(self, userid, name, tracks, desc='Top 50 songs from the past month'):
        playlist_id = spotify_api.create_playlist(self._auth, userid, name, desc)
        # if playlist population fails, playlist will be deleted
        try:
            spotify_api.populate_playlist(self._auth, playlist_id, tracks)
        except BadRequestError:
            spotify_api.delete_playlist(self._auth, playlist_id)
            raise BadRequestError

    # returns json object containing all playlists and data
    def get_all_playlists(self):
        return spotify_api.get_all_playlists(self._auth)

    # finds playlist id
    def find_playlist_id(self, playlist_name):
        all_playlists = self.get_all_playlists()
        for playlist in all_playlists['items']:
            # print(playlist['name'])
            if playlist['name'].lower() == playlist_name.lower():
                print('found playlist')
                return playlist['id']
        print('did not find playlist')
        return None

    # extracts list of tracks+artists from a playlist
    def extract_tracks_and_artists_from_playlist(self, playlist_name):
        playlist_id = self.find_playlist_id(playlist_name)

        # do while loop to grab all tracks form playlist
        list_of_tracks = []
        more_tracks = True
        offset = 0
        while more_tracks:
            playlist_tracks = spotify_api.get_tracks_from_playlist(self._auth, playlist_id, offset)
            for item in playlist_tracks['items']:
                track = item['track']['name']
                artist = item['track']['artists'][0]['name']
                id = item['track']['id']
                # print(f'{track} by {artist}')
                list_of_tracks.append((track, artist, id))

            if playlist_tracks['next'] is not None:
                # print('more tracks')
                offset += 100
            else:
                more_tracks = False
        return list_of_tracks
