import csv

from monthlify.data import data_manager
from monthlify.data import PlaylistManager
from monthlify.data import lyric_analyzer


class Analyzer:

    def __init__(self):
        self.dm = data_manager.DataManager()
        self.pm = PlaylistManager()

    def get_track_data_for_playlist(self, playlist_name):
        tracks = self.pm.extract_tracks_and_artists_from_playlist(playlist_name)
        track_ids = []
        sentiment_analysis_list = []
        for track in tracks:
            track_ids.append(track[2])
            analysis = lyric_analyzer.sentiment_analysis(track[0], track[1])
            sentiment_analysis_list.append(analysis)

        audio_features_list = self.dm.analyze_tracks(track_ids)[3]

        summary_list = []
        with open(f'./monthlify/data/playlists/{playlist_name}.csv', mode='w') as file:
            data_writer = csv.writer(file, delimiter=',')
            data_writer.writerow(['Track', 'Artist',
                                  'Energy', 'Tempo',
                                  'Valence', 'Sentiment Score',
                                  'Lexical Richness'])
            for i in range(len(tracks)):
                # create tuple of track, artist, energy, tempo, valence, sentiment analysis score, lexical richness
                if sentiment_analysis_list[i] is not None:
                    sentiment_analysis = sentiment_analysis_list[i][0]
                    lexical_richness = sentiment_analysis_list[i][1]
                else:
                    sentiment_analysis, lexical_richness = None, None

                track_data = (tracks[i][0],
                              tracks[i][1],
                              audio_features_list[i][0],
                              audio_features_list[i][1],
                              audio_features_list[i][2],
                              sentiment_analysis,
                              lexical_richness)
                summary_list.append(track_data)
                data_writer.writerow(track_data)

        return summary_list
