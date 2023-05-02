from html.parser import HTMLParser
from dataclasses import dataclass
import urllib.request
import urllib.parse
import os
import shutil
from decorators import require_icons

HEADERS = {'User-Agent': 'Mozilla/5.0'}

@dataclass
class Icon:
    url: str
    width: int = 0
    height: int = 0

    def save(self):
        parsed_url = urllib.parse.urlparse(self.url)
        save_dir = parsed_url.hostname
        filename = os.path.basename(parsed_url.path)
        
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        _request = urllib.request.Request(self.url, headers=HEADERS)
        with urllib.request.urlopen(_request) as response:
            with open(os.path.join(save_dir, filename), "wb") as out_file:
                return shutil.copyfileobj(response, out_file)

class Metadata(HTMLParser):
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.icons = []
        self.title = None

        self._match_title = False

        _request = urllib.request.Request(self.url, headers=HEADERS)
        
        with urllib.request.urlopen(_request) as response:
            html = str(response.read())

        self.feed(html)

    @require_icons
    def best(self):
        resolution = {}
        for icon in self.icons:
            if int(icon.width) > 0 and int(icon.height) > 0:
                calculated_res = int(icon.width) + int(icon.height)
                resolution[calculated_res] = icon
            else:
                resolution[0] = self.icons[0]
        
        best_res = list(dict(sorted(resolution.items(), reverse=True)).keys())[0]
        return resolution[best_res]

    def handle_starttag(self, tag, attrs):
        # Only parse the 'link' tag.
        width = 0
        height = 0
        if tag == "link":
            for item in attrs:
                if "rel" and "icon" in item:
                    for item2 in attrs:
                        if "href" in item2:
                            for item3 in attrs:
                                if "sizes" in item3:
                                    width = item3[1].split("x")[0]
                                    height = item3[1].split("x")[1]
                            self.icons.append(Icon(self.url + item2[1], width, height))
        
        if tag == "title":
            self._match_title = True

    def handle_data(self, data):
        if self._match_title:
            self.title = data
            self._match_title = False