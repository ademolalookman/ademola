import requests
import base64
import re
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import os
from datetime import datetime

class HDFilmIzleScraper:
    def __init__(self):
        self.base_url = "https://www.hdfilmizle.net"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })

    def get_page_movies(self, page_num=1):
        url = f"{self.base_url}/page/{page_num}"
        print(f"  Sayfa {page_num} Çekiliyor : {url}")
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            movies = []
            movie_elements = soup.select('div#moviesListResult a.poster')

            for element in movie_elements:
                try:
                    title_elem = element.select_one('h2.title')
                    title = title_elem.get_text(strip=True) if title_elem else ""
                    href = element.get('href', '')
                    if href and not href.startswith('http'):
                        href = urljoin(self.base_url, href)
                    img_elem = element.select_one('img')
                    poster_url = ""
                    if img_elem:
                        poster_url = img_elem.get('data-src') or img_elem.get('src', '')
                        if poster_url and not poster_url.startswith('http'):
                            poster_url = urljoin(self.base_url, poster_url)
                    year_elem = element.select_one('.poster-year')
                    year = year_elem.get_text(strip=True) if year_elem else ""
                    genre_elem = element.select_one('.poster-genres')
                    genre = genre_elem.get_text(strip=True) if genre_elem else ""

                    if title and href:
                        movies.append({
                            'title': title,
                            'url': href,
                            'poster': poster_url,
                            'year': year,
                            'genre': genre
                        })
                except Exception as e:
                    print(f"hata: {e}")
                    continue
            return movies
        except Exception as e:
            print(f"sayfa {page_num} çekilemedi: {e}")
            return []

    def get_movie_details(self, movie_url):
        try:
            response = self.session.get(movie_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            iframe = soup.select_one('iframe')
            if not iframe:
                return None
            iframe_url = iframe.get('data-src') or iframe.get('src')
            if not iframe_url:
                return None
            if not iframe_url.startswith('http'):
                iframe_url = urljoin(self.base_url, iframe_url)
            stream_url = self.extract_stream_url(iframe_url)
            return {
                'iframe_url': iframe_url,
                'stream_url': stream_url
            }
        except Exception as e:
            print(f"bu filmde hata {movie_url}: {e}")
            return None

    def extract_stream_url(self, iframe_url):
        try:
            response = self.session.get(iframe_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            script_content = ""
            for script in soup.find_all('script'):
                if script.string and 'sources:' in script.string:
                    script_content = script.string
                    break
            if not script_content:
                return None
            regex = r'EE\.dd\("([^"]+)"\)'
            matches = re.findall(regex, script_content)
            for encoded_data in matches:
                try:
                    decoded_url = self.decode_vidrame_url(encoded_data)
                    if decoded_url and decoded_url.startswith('http'):
                        return decoded_url
                except:
                    continue
            return None
        except Exception as e:
            print(f"bu iframeden çekilemedi {iframe_url}: {e}")
            return None

    def decode_vidrame_url(self, encoded_data):
        try:
            video = encoded_data.replace('-', '+').replace('_', '/')
            while len(video) % 4 != 0:
                video += '='
            decoded_bytes = base64.b64decode(video)
            decoded_str = decoded_bytes.decode('utf-8', errors='ignore')
            rot13_decoded = self.rot13_decode(decoded_str)
            final_url = rot13_decoded[::-1]
            return final_url
        except Exception as e:
            print(f"vidrame hata {e}")
            return None

    def rot13_decode(self, text):
        result = ""
        for char in text:
            if char.isalpha():
                base = ord('A') if char.isupper() else ord('a')
                result += chr((ord(char) - base + 13) % 26 + base)
            else:
                result += char
        return result

    def save_playlist(self, content, filename):
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"playlit hatası {e}")
            return False

    def scrape_and_create_playlist(self, filename="hdfilmizle.m3u"):
        m3u_content = "#EXTM3U\n"
       

        successful_movies = 0
        total_movies = 0
        page = 1

        while True:
            movies = self.get_page_movies(page)
            if not movies:
                print(f" sayfa {page} daha film yok Kapanıyor")
                break

            print(f"--- sayfa {page} | {len(movies)} tane film bulundu  ---")

            for movie in movies:
                total_movies += 1
                print(f"Film {total_movies}: {movie['title']}")
                try:
                    details = self.get_movie_details(movie['url'])
                    if details and details['stream_url']:
                        info = f"{movie['title']}"
                        if movie['year']:
                            info += f" ({movie['year']})"

                        m3u_content += f"#EXTINF:-1"
                        m3u_content += f' group-title="Filmler" tvg-name="{movie["title"]}"'
                        if movie['poster']:
                            m3u_content += f' tvg-logo="{movie["poster"]}"'
                        m3u_content += f",{info}\n{details['stream_url']}\n\n"
                        successful_movies += 1
                    else:
                        print(f"❌ Stream bulunamadı: {movie['title']}")
                except Exception as e:
                    print(f"❌ Hata: {movie['title']} - {e}")
                time.sleep(1)

            page += 1
            time.sleep(1)

        print(f"\n🎉 {successful_movies}/{total_movies} film başarıyla işlendi.")
        if self.save_playlist(m3u_content, filename):
            print(f"✅ Playlist kaydedildi: {filename}")
            print(f"📁 Boyut: {os.path.getsize(filename)} bytes")
        else:
            print("❌ Playlist kaydedilemedi.")

def main():
    scraper = HDFilmIzleScraper()
    
    scraper.scrape_and_create_playlist()

if __name__ == "__main__":
    main()
