from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests 

# URL of the events page
# url = "https://johnnybrendas.com/events/"

# # Set up Selenium with Chrome
# chrome_options = Options()
# chrome_options.add_argument("--headless")  # Run in headless mode
# chrome_options.add_argument("--disable-gpu")
# chrome_options.add_argument("--no-sandbox")

# driver = webdriver.Chrome()
# driver.get(url)

# # Wait for the page to load and find event titles
# event_titles = driver.find_elements(By.CLASS_NAME, "rhp-event__title--grid")

# # Print the text of each event title
# for title in event_titles:
#     print(title.text)

# driver.quit()

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id="b7c003cf3977459a9063e4a027b23b36",
    client_secret="248073e7c10c421093975f33973929c5",
    redirect_uri="https://www.philly-mappy-hour.com/",
    scope="playlist-modify-public"
))

results = sp.search(q='TEEN MORTGAGE', type='artist', limit=1)
print(results) # type: ignore
print(results) # type: ignore
artists = results.get('artists', {}).get('items', []) # type: ignore
print(artists) # type: ignore
if not artists:
    print(f"No match for {'TEEN MORTGAGE'}")
artist_id = artists[0]['id']
print(artist_id) # type: ignore
top_tracks = sp.artist_top_tracks(artist_id)
print(top_tracks) # type: ignore
print([track['uri'] for track in top_tracks['tracks'][:limit]]) # type: ignore


def get_top_tracks(artist_name, limit=3):
    results = sp.search(q=artist_name, type='artist', limit=1)
    artists = results.get('artists', {}).get('items', []) # type: ignore
    if not artists:
        print(f"No match for {artist_name}")
        return []
    artist_id = artists[0]['id']
    top_tracks = sp.artist_top_tracks(artist_id)
    return [track['uri'] for track in top_tracks['tracks'][:limit]] # type: ignore

def create_playlist_and_add_tracks(user_id, playlist_name, all_uris):
    playlist = sp.user_playlist_create(user=user_id, name=playlist_name)
    sp.playlist_add_items(playlist_id=playlist['id'], items=all_uris) # type: ignore
    print(f"Playlist '{playlist_name}' created with {len(all_uris)} tracks!")