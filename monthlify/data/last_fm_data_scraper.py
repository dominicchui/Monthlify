import requests
import datetime
import json
import xml.etree.ElementTree as ET

user_name =''

# Finds the top 50 tracks of the past month from the user's last.fm account
# params: filename--name of the soon to be created file that will hold the data
#         username--last.fm username
# writes the data as an xml file
def get_data(filename, username):
    key = ""
    link = f'http://ws.audioscrobbler.com/2.0/?method=user.gettoptracks&user={username}&period=1month&api_key={key}'

    f = requests.get(link)

    with open(f'./raw/{filename}.xml', mode='w', encoding='utf-8') as file:
        file.write(f.text)


# interprets the raw xml data obtained from get_data
# params: filename--name of the raw data file
# writes results as json array with (song, artist) lists as values
def parse_data(filename):
    tree = ET.parse(f'./raw/{filename}.xml')
    root = tree.getroot()
    with open(f'./json/{filename}.json', mode='w', encoding='utf-8') as file:
        tracks = []
        for track in root.findall("./toptracks/track"):
            song = track.find("name").text
            artist = track.find("artist/name").text
            tracks.append((song, artist))
        json.dump(tracks, file)


def main():
    date = datetime.date.today()
    filename = f'{date.year}_{date.month}_{date.day}'
    get_data(filename, user_name)
    parse_data(filename)


if __name__ == '__main__':
    main()

