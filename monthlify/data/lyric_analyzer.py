import string
import requests
import re
from nltk.corpus import stopwords
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from bs4 import BeautifulSoup


# scrapes the track lyrics from genius
def get_lyrics(track_name, artist_name):
    # find the appropriate genius url
    base_url = 'https://genius.com'

    # remove extra characters that muddle the lyric search
    track_name = track_name.partition(' -')[0]
    track_name = track_name.replace('&', 'and')
    track_name = track_name.translate(str.maketrans('', '', string.punctuation))
    track_name = track_name.replace(' ', '-').lower()
    artist_name = artist_name.replace('&', 'and')
    artist_name = artist_name.translate(str.maketrans('', '', string.punctuation))
    artist_name = artist_name.replace(' ', '-').lower()
    url = f'{base_url}/{artist_name}-{track_name}-lyrics'
    print(url)

    # parse the html
    try:
        page = requests.get(url)
        html_contents = BeautifulSoup(page.text, 'html.parser')
        lyrics = html_contents.find('div', class_='lyrics').get_text()
        # print(lyrics)
    except AttributeError:
        lyrics = None
        print(f'{track_name} by {artist_name} lyrics not found')
    return lyrics


# remove meta comments like [chorus]
def first_pass_sanitize_lyrics(lyrics):
    lyrics = re.sub(r'[(\[].*?[)\]]', '', lyrics)

    return lyrics


# turns the input into word tokens
def tokenize_lyrics_word(lyrics):
    lyrics = lyrics.replace('\n', ' ')
    words = [word.strip(string.punctuation) for word in lyrics.split(" ")]
    filtered_words = {word for word in words if word not in stopwords.words('english')}
    if '' in filtered_words:
        filtered_words.remove('')
    return filtered_words


# turns the input into sentence tokens
def tokenize_lyrics_sentence(lyrics):
    lines = lyrics.split('\n')
    if '' in lines:
        lines.remove('')
    return lines


# turns the input into "paragraph" tokens
def tokenize_lyrics_paragraph(lyrics):
    lines = lyrics.split('\n\n')
    if '' in lines:
        lines.remove('')
    return lines


def get_lexical_richness(lyrics):
    tokenized_lyrics = tokenize_lyrics_word(lyrics)
    words = [word.strip(string.punctuation) for word in lyrics.split(" ")]

    return len(tokenized_lyrics) / len(words) * 100


def test_sentiment_analysis(track, artist):
    lyrics = get_lyrics(track, artist)
    if lyrics:
        sanitized_lyrics = first_pass_sanitize_lyrics(lyrics)
        print('sentence:\n')
        sentence_sentiment_analysis(sanitized_lyrics)
        print('\nparagraph:\n')
        paragraph_sentiment_analysis(sanitized_lyrics)
        print('\nwhole text:\n')
        whole_sentiment_analysis(sanitized_lyrics)


def sentence_sentiment_analysis(lyrics):
    lines = tokenize_lyrics_sentence(lyrics)
    return token_sentiment_analysis(lines)


def paragraph_sentiment_analysis(lyrics, verbose=False):
    paragraphs = tokenize_lyrics_paragraph(lyrics)
    return token_sentiment_analysis(paragraphs, verbose)


def whole_sentiment_analysis(lyrics):
    tokens = [lyrics]
    return token_sentiment_analysis(tokens)


def token_sentiment_analysis(tokens, verbose=False):
    sid = SentimentIntensityAnalyzer()

    sentiment_sum, positive_lines, neutral_lines, negative_lines = 0, 0, 0, 0

    for line in tokens:
        score = sid.polarity_scores(line)
        if verbose:
            print(score)
            print(line)
        score = score['compound']
        sentiment_sum += score
        if score >= 0.3:
            positive_lines += 1
        elif score <= -0.3:
            negative_lines += 1
        else:
            neutral_lines += 1

    if verbose:
        print(f'sentiment sum: {sentiment_sum}')
        print(f'positive lines: {positive_lines}, {positive_lines/len(tokens)*100}%')
        print(f'neutral lines: {neutral_lines}, {neutral_lines/len(tokens)*100}%')
        print(f'negative lines: {negative_lines}, {negative_lines/len(tokens)*100}%')

    return sentiment_sum


def sentiment_analysis(track_name, artist_name, verbose=False):
    lyrics = get_lyrics(track_name, artist_name)
    if lyrics:
        clean = first_pass_sanitize_lyrics(lyrics)
        lexical_richness = get_lexical_richness(clean)
        analysis = paragraph_sentiment_analysis(clean, verbose)
        return analysis, lexical_richness
    else:
        return None
