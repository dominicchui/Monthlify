import json
from collections import defaultdict

from monthlify.data import spotify_api
from monthlify.auth import authenticate
from monthlify.core import read_config


class DayData:

    def __init__(self, date):
        self._conf = read_config()
        self._auth = authenticate(self._conf)

        self.dict = defaultdict(int)
        self.date = date
        self.artists = defaultdict(int)
        self.meta_data = ()
        self.total_plays = 0

    # add a track to the day
    # params: track_info--tuple of (track, artist, album, track id)
    def add(self, track_info):
        assert len(track_info) == 4
        self.dict[track_info] += 1
        artist = track_info[1]
        self.artists[artist] += 1
        self.total_plays += 1

    # gets the tracks in order of number of times played
    def most_common_tracks(self):
        return sorted(self.dict.items(), key=lambda kv: kv[1], reverse=True)

    def most_common_artists(self):
        return sorted(self.artists.items(), key=lambda kv: kv[1], reverse=True)

    # meta data is calculated every time it is got instead of every time a track is added
    @property
    def meta_data(self):
        tracks = [item[0][3] for item in self.dict.items()]

        track_split = [tracks[i * 100:(i+1) * 100] for i in range((len(tracks) + 99)//100)]

        energy_avg, tempo_avg, valence_avg = 0, 0, 0

        for track_list in track_split:
            results = spotify_api.get_features(self._auth, track_list)

            for sub_list in results:
                for item in sub_list["audio_features"]:
                    energy_avg += item["energy"]
                    tempo_avg += item["tempo"]
                    valence_avg += item["valence"]

        energy_avg /= len(tracks)
        tempo_avg /= len(tracks)
        valence_avg /= len(tracks)

        # print(f'energy average = {energy_avg:.3f}')
        # print(f'tempo average = {tempo_avg:.1f}')
        # print(f'valence average = {valence_avg:.3f}')

        return energy_avg, tempo_avg, valence_avg

    # shouldn't ever need to set meta_data
    @meta_data.setter
    def meta_data(self, value):
        self._meta_data = value

    # writes the class to disk, overwriting previous (hopefully obsolete) data
    def persist(self):
        # get the meta data
        artists = self.most_common_artists()
        analysis = self.meta_data
        # not every day will have 5 artists played
        top_artists = artists[:5]

        top_artists_dict = []
        for i in range(len(top_artists)):
            top_artists_dict.append((top_artists[i][0], top_artists[i][1]))

        parent_list = []
        meta_dict = {'total plays': self.total_plays,
                     'top artists': top_artists_dict,
                     'average energy': f'{analysis[0]:.3f}',
                     'average tempo': f'{analysis[1]:.1f}',
                     'average valence': f'{analysis[2]:3f}'
                     }
        parent_list.append(meta_dict)

        track_list = []
        for key, value in self.dict.items():
            track, artist, album, track_id = key
            json_dict = {'track': track,
                         'artist': artist,
                         'album': album,
                         'track_id': track_id,
                         'plays': value}
            track_list.append(json_dict)
        parent_list.append(track_list)

        with open(f'./play_log/days/{self.date}.json', mode='w') as file:
            json.dump(parent_list, file, indent=2, separators=(',', ':'))

        print('file written')
