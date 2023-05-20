from html.parser import HTMLParser
from dataclasses import dataclass
import urllib.request
import urllib.parse
import os
import shutil
from website_metadata.decorators import require_icons
from urllib.error import URLError, HTTPError
import uuid

HEADERS = {'User-Agent': 'Mozilla/5.0'}

def is_valid_url(url):
    try:
        result = urllib.parse.urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

@dataclass
class Icon:
    url: str
    width: int = 0
    height: int = 0

    def save(self, output=""):
        parsed_url = urllib.parse.urlparse(self.url)        
        if parsed_url.hostname:
            hostname = parsed_url.hostname
        else:
            hostname = uuid.uuid4().hex
        save_dir = os.path.join(output, hostname)
        filename = os.path.basename(parsed_url.path)

        if save_dir.endswith("."):
            save_dir = save_dir[:-1]

        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        _request = urllib.request.Request(self.url, headers=HEADERS)
        try:
            with urllib.request.urlopen(_request) as response:
                with open(os.path.join(save_dir, filename), "wb") as out_file:
                    return shutil.copyfileobj(response, out_file)
        except URLError as error:
            print("Unable to save file")
            return None
            

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
        self.status = None
        self.language = None

        self.robots = self.get_robots()
        self.sitemap = self.get_sitemap()
        self.humans = self.get_humans()

        self._match_title = False

        _request = urllib.request.Request(self.url, headers=HEADERS)
        
        try:
            with urllib.request.urlopen(_request, timeout=10) as response:
                self.raw_html = str(response.read())
                self.respheader = ResponseHeader(server=response.headers.get("Server"), x_powered_by=response.headers.get("X-Powered-By"))
                self.raw_respheader = response.headers
                self.status = response.status
            self.feed(self.raw_html)
        except HTTPError as error:
            self.status = error.code
            self.raw_respheader = error.headers
        except TimeoutError:
            self.status = 408


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

        if tag == "html":
            for item in attrs:
                if "lang" in item:
                    self.language = item[1]

        if tag == "link":
            for item in attrs:
                if "rel" and "icon" in item:
                    for item2 in attrs:
                        if "href" in item2:
                            for item3 in attrs:
                                if "sizes" in item3:
                                    if item3[1] == "any":
                                        width = 0
                                        height = 0
                                    else:
                                        width = item3[1].split("x")[0]
                                        height = item3[1].split("x")[1]

                            if is_valid_url(item2[1]):
                                self.icons.append(Icon(item2[1], width, height))
                            elif item2[1].startswith("data:"):
                                self.icons.append(Icon(item2[1], width, height))
                            elif item2[1].startswith("//"):
                                self.icons.append(Icon("https://" + item2[1][2:], width, height))
                            else:
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