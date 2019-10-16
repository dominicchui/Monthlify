import json
import datetime
import os
import re
from collections import defaultdict

from monthlify.auth import authenticate
from monthlify.core import read_config
from monthlify.data.spotify_api import get_features
from monthlify.data.spotify_api import get_recently_played
from monthlify.data import PlaylistManager
import monthlify.data.day_data as day_data

# adjusts the timezone for a given time
# params: time--string of the time to be adjusted e.g. (2019-08-04T08:40:30.880Z)
#         shift--int difference from UTC; e.g. +8 or -8
# return: a string of the adjusted time with embedded timezone info
def adjust_time_zone(time, shift):
    offset = datetime.timedelta(hours=shift)
    try:
        datetime_obj = datetime.datetime.strptime(time, '%Y-%m-%dT%H:%M:%S.%fZ')
        adjusted_time = datetime_obj + offset
        adjusted_time = adjusted_time.replace(tzinfo=datetime.timezone(offset))
        time_string = adjusted_time.strftime('%Y-%m-%dT%H:%M:%S.%f%z')
    except ValueError:
        datetime_obj = datetime.datetime.strptime(time, '%Y-%m-%dT%H:%M:%SZ')
        adjusted_time = datetime_obj + offset
        adjusted_time = adjusted_time.replace(tzinfo=datetime.timezone(offset))
        time_string = adjusted_time.strftime('%Y-%m-%dT%H:%M:%S%z')

    return time_string


# determines spotify ID from spotify URI
# params: tracks--a list of URIs
# return: a list of IDs
def get_track_ids(tracks):
    for i in range(len(tracks)):
        tracks[i] = tracks[i][14:]
    return tracks


# determines spotify URI from spotify ID
# params: tracks--a list of IDs
# return: a list of URIs
def get_track_uris(tracks):
    uris = []
    for i in range(len(tracks)):
        uri = 'spotify:track:' + tracks[i]
        uris.append(uri)
    return uris


# extracts a DayData object for a given date
# params: date--format YYYY-MM-DD
# return: a DayData object
def extract_day_data(date):
    # check if file exists, if so, import data
    file_path = f'./play_log/days/{date}.json'
    day = day_data.DayData(date)
    if os.path.isfile(file_path):
        with open(file_path, mode='r') as read_file:
            print('grabbing old data')
            contents = json.load(read_file)
            for item in contents[1]:
                track = item['track']
                artist = item['artist']
                album = item['album']
                track_id = item['track_id']
                for i in range(item['plays']):
                    day.add((track, artist, album, track_id))
    return day


# merges any number of dicts with key overlap by combining and summing their values
# accepts either dicts or lists of dicts as arguments
def merge_dicts(*args):
    merged_dict = defaultdict(int)
    for arg in args:
        if isinstance(arg, dict):
            for key, value in arg.items():
                merged_dict[key] += value
        if isinstance(arg, list):
            for item in arg:
                if isinstance(item, dict):
                    for key, value in item.items():
                        merged_dict[key] += value
    return merged_dict


class DataManager:

    def __init__(self, username):
        self._conf = read_config()
        self._auth = authenticate(self._conf)
        self.user_name = username

    # scrapes the recent track data and processes it
    def get_recent_play_data(self, last_scraped=0):
        # reauthenticate in case token has expired
        self._auth = authenticate(self._conf)
        filename = get_recently_played(self._auth, last_scraped)
        self._trim_play_log(filename)
        self.process_play_log(filename)

    # processes the raw json datafile by trimming away extraneous info
    # saves the trimmed data file in /data/json and does not touch raw file (unless empty)
    # params: filename--name of the raw json datafile in the play_log raw dir
    def _trim_play_log(self, filename):
        with open(f'./play_log/raw/{filename}', mode='r') as file:
            result = json.load(file)

            # if raw file contains no play info, just delete it
            if not len(result["items"]):
                os.remove(f'./play_log/raw/{filename}')
                print("null file removed")
                return

            result_list = []
            for i in range(len(result['items'])):
                track = result["items"][i]["track"]["name"]
                artist = result["items"][i]["track"]["artists"][0]["name"]
                album = result["items"][i]["track"]["album"]["name"]
                track_id = result["items"][i]["track"]["id"]
                time = result["items"][i]["played_at"]
                adj_time = adjust_time_zone(time, -6)

                track_data_dict = {'track': track,
                                   'artist': artist,
                                   'album': album,
                                   'track_id': track_id,
                                   'time': adj_time}
                result_list.append(track_data_dict)

            with open(f'./play_log/trimmed/{filename}', mode='w') as out_file:
                json.dump(result_list, out_file, indent=2, separators=(',', ':'))
                print("trimmed file written")

    # processes the given play log by creating daydata objects, populating with data, and persisting
    # params: filename--name of the json file to be processed
    def process_play_log(self, filename):
        print(f'processing {filename}')
        try:
            with open(f'./play_log/trimmed/{filename}', mode='r') as data_file:
                data = json.load(data_file)

                # collect all the data for each play
                # temporarily store as (track data, date, id) tuples in a list
                plays_by_day = defaultdict(list)
                for item in data:
                    track_data = (item['track'], item['artist'], item['album'], item['track_id'])
                    date_str = item['time']
                    date = datetime.datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%f%z').date()
                    plays_by_day[date].append(track_data)
                # key is a date and value is a list of tuples; write a file for each date
                for key, value in plays_by_day.items():
                    print(f'processing play log date: {key}')
                    # check for existing file and extract data
                    day = extract_day_data(key)

                    # integrate new data
                    print('integrating new data')
                    for track_tuple in value:
                        day.add(track_tuple)
                    day.persist()
        # if the data file was null and deleted, do nothing
        except FileNotFoundError:
            return

    def write_summary_for_date_range(self, start_date, end_date):
        start = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
        step = datetime.timedelta(days=1)

        print('finding top tracks')
        top_tracks = self.get_most_played_tracks(start_date, end_date, 10)
        print('finding top artists')
        top_artists = self.get_most_played_artists(start_date, end_date, 10)
        print('finding meta data')
        meta_data = self.analyze_data_date_range(start_date, end_date)

        with open(f'./play_log/summaries/{start_date}-{end_date}.txt', mode='w') as file:
            file.write(f'Summary for {start_date} to {end_date}\n')

            # write top tracks
            file.write(f'\tTop Tracks:\n')
            for track in top_tracks:
                file.write(f'\t\t{track[0][0]} by {track[0][1]} with {track[1]} plays\n')

            # write top artists
            file.write(f'\tTop Artists:\n')
            for artist in top_artists:
                file.write(f'\t\t{artist[0]} with {artist[1]} plays\n')

            # write meta data
            file.write(f'\tAverage Energy: {meta_data[0]:.3f}\n')
            file.write(f'\tAverage Tempo: {meta_data[1]:.1f}\n')
            file.write(f'\tAverage Valence: {meta_data[2]:.3f}\n\n')

            # write data for each day
            while start <= end:
                start_string = start.strftime('%Y-%m-%d')
                file.write(f'{start_string}\n')

                # get the meta data
                artists = self.get_most_played_artists(start_string)
                analysis = self.analyze_data_date_range(start_string)
                # not every day will have 5 artists played
                top_artists = artists[:5]
                total_plays = 0
                for artist in artists:
                    total_plays += artist[1]
                file.write(f'\tTotal Plays: {total_plays}')
                file.write(f'\tTop Artists:\n')
                for i in range(len(top_artists)):
                    file.write(f'\t\t{top_artists[i][0]} with {top_artists[i][1]} plays\n')

                file.write(f'\tAverage Energy: {analysis[0]:.3f}\n')
                file.write(f'\tAverage Tempo: {analysis[1]:.1f}\n')
                file.write(f'\tAverage Valence: {analysis[2]:.3f}\n\n')

                start += step

    def _get_dict_from_date_range(self, start_date, end_date):
        start = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
        step = datetime.timedelta(days=1)
        dict_list = []
        while start <= end:
            print(f'get_dict_from_date_range: {start}')
            day = extract_day_data(start)
            dict_list.append(day.dict)
            start += step
        merged_dict = merge_dicts(dict_list)
        return merged_dict

    # gets top tracks played sorted from most to least in the given time frame
    # params: start_date & end_date: YYYY-MM-DD
    #         number--number of tracks to return
    #         make_playlist--boolean whether to turn the results into a playlist
    # return: a list sorted by plays as a list of tuples of track data tuple and plays
    def get_most_played_tracks(self, start_date, end_date=None, number=50, make_playlist=False):

        # easier way to look at just one date
        if end_date is None:
            end_date = start_date

        merged_dict = self._get_dict_from_date_range(start_date, end_date)
        sorted_list = sorted(merged_dict.items(), key=lambda kv: kv[1], reverse=True)
        if make_playlist:
            # convert IDs into URIs
            id_list = []
            for i in range(number):
                id_list.append(sorted_list[i][0][3])
            uri_list = get_track_uris(id_list)

            # make the playlist
            pm = PlaylistManager()
            pm.prepare_playlist(self.user_name, f'{start_date} to {end_date}', uri_list,
                                f'Top {number} songs from {start_date} to {end_date}')

        return sorted_list[:number]

    # gets top artists played sorted from most to least in the given time frame
    # params: start_date & end_date: YYYY-MM-DD
    #         number--number of tracks to return
    # return: a list of artists sorted by plays
    def get_most_played_artists(self, start_date, end_date=None, number=20):

        if end_date is None:
            end_date = start_date

        merged_dict = self._get_dict_from_date_range(start_date, end_date)
        artist_dict = defaultdict(int)
        for key, value in merged_dict.items():
            artist_dict[key[1]] += value
        sorted_list = sorted(artist_dict.items(), key=lambda kv: kv[1], reverse=True)
        return sorted_list[:number]

    # returns the timestamp of the most recent log in the form
    # YYYY-MM-DD HH-MM-SS:ffffff
    def get_most_recent_log_time(self):
        files = os.listdir('./play_log/raw')
        paths = [os.path.join('./play_log/raw', basename) for basename in files
                 if basename.endswith('.json')]
        file_name = max(paths, key=os.path.getctime)

        # use regex to grab the datetime info
        match_obj = re.match('./play_log/raw/(.*).json', file_name)

        assert match_obj
        datetime_str = match_obj.group(1)

        datetime_obj = datetime.datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S.%f')
        return datetime_obj

    # analyzes the tracks using spotify data
    # params: tracks--either list of track_ids or list of tuples of track tuples + plays
    #   e.g. what get_most_played_tracks returns
    def analyze_tracks(self, tracks):

        assert tracks

        if isinstance(tracks[0][0], tuple):
            print('grabbing IDs')
            tracks = [item[0][3] for item in tracks]
        results = get_features(self._auth, tracks)

        audio_feature_list = []

        energy_avg, tempo_avg, valence_avg = 0, 0, 0
        for sub_list in results:
            for item in sub_list["audio_features"]:
                energy_avg += item["energy"]
                tempo_avg += item["tempo"]
                valence_avg += item["valence"]
                audio_feature_list.append((item["energy"],
                                           item["tempo"],
                                           item["valence"]))

            energy_avg /= len(sub_list["audio_features"])
            tempo_avg /= len(sub_list["audio_features"])
            valence_avg /= len(sub_list["audio_features"])

        return energy_avg, tempo_avg, valence_avg, audio_feature_list

    # analyze the tracks from a date range using spotify data
    # params: start_date & end_date--strings in format YYYY-MM-DD
    def analyze_data_date_range(self, start_date, end_date=None):

        if end_date is None:
            end_date = start_date

        total_plays = 0
        energy = 0
        tempo = 0
        valence = 0
        start = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
        step = datetime.timedelta(days=1)
        while start <= end:
            print(f'analyze_data_date_range: {start}')
            day = extract_day_data(start)
            if day.total_plays:
                total_plays += day.total_plays
                meta_data = day.meta_data
                energy += meta_data[0] * day.total_plays
                tempo += meta_data[1] * day.total_plays
                valence += meta_data[2] * day.total_plays
            start += step
        if total_plays:
            energy /= total_plays
            tempo /= total_plays
            valence /= total_plays

        return energy, tempo, valence
