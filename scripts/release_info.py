import json
from urllib.request import urlopen


def downloadResource(url):
    response = urlopen(url)
    data = response.read()
    return data.decode("utf-8")


def getReleaseInfo():
    return json.loads(
        downloadResource(
            "https://api.github.com/repos/fontra/fontra-pak/releases/latest"
        )
    )
