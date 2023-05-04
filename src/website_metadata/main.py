from html.parser import HTMLParser
from dataclasses import dataclass
import urllib.request
import urllib.parse
import os
import shutil
from website_metadata.decorators import require_icons
from urllib.error import URLError, HTTPError

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

@dataclass
class ResponseHeader:
    server: str
    x_powered_by: str

class Metadata(HTMLParser):
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.icons = []
        self.title = None
        self.description = None
        self.respheader = None
        self.raw_respheader = None
        self.raw_html = None
        self.robots = self.get_robots()
        self.sitemap = self.get_sitemap()
        self.humans = self.get_humans()

        self._match_title = False

        _request = urllib.request.Request(self.url, headers=HEADERS)
        
        with urllib.request.urlopen(_request) as response:
            self.raw_html = str(response.read())
            self.respheader = ResponseHeader(server=response.headers.get("Server"), x_powered_by=response.headers.get("X-Powered-By"))
            self.raw_respheader = response.headers

        self.feed(self.raw_html)


    def get_robots(self):
        _request = urllib.request.Request(urllib.parse.urljoin(self.url, "robots.txt"), headers=HEADERS)
        try:
            with urllib.request.urlopen(_request) as response:
                return response.read()
        except HTTPError as error:
            if error.code == 404:
                return None
    
    def get_sitemap(self):
        _request = urllib.request.Request(urllib.parse.urljoin(self.url, "sitemap.xml"), headers=HEADERS)
        try:
            with urllib.request.urlopen(_request) as response:
                return response.read()
        except HTTPError as error:
            if error.code == 404:
                return None
    
    def get_humans(self):
        _request = urllib.request.Request(urllib.parse.urljoin(self.url, "humans.txt"), headers=HEADERS)
        try:
            with urllib.request.urlopen(_request) as response:
                return response.read()
        except HTTPError as error:
            if error.code == 404:
                return None


    @require_icons
    def best_icon(self):
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
        if tag == "meta":
            for item in attrs:
                if "description" in item:
                    for item2 in attrs:
                        if "content" in item2:
                            self.description = item2[1]

    def handle_data(self, data):
        if self._match_title:
            self.title = data
            self._match_title = False