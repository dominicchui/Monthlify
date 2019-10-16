# Monthlify
(Disclaimer: this is a work in progress.)

A python app that uses the Spotify API to log listening data, create playlists based on the data from any arbitrary period of time, and deploys natural language processing to perform sentiment analysis for sentiment-based playlists.


Code as seen will not actually work because I do not wish to give out keys and have not set up a server to handle requests yet.

Steps to make it work:
  1) acquire a spotify api key and add to config.yaml
  2) add username to play_scraper.py
  3) run spotify_auth.py and follow instructions to authorize app
  4) run data_scraper.py to get most recent spotify data
  5) open a python interpreter, create a DataManager object, and call methods like "get_most_played_tracks" to retrieve data
  6) call "get_track_data_for_playlists" in analyzer.py to get sentiment analysis for tracks in a playlist

