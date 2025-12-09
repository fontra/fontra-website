import json
import pathlib
from urllib.request import urlopen
import lxml.html


def downloadResource(url):
    response = urlopen(url)
    data = response.read()
    return data.decode("utf-8")


thisDir = pathlib.Path(__file__).resolve().parent
docsDir = thisDir.parent / "docs"
indexPath = docsDir / "index.html"

releaseInfo = json.loads(
    downloadResource("https://api.github.com/repos/fontra/fontra-pak/releases/latest")
)

doc = lxml.html.parse(indexPath)
root = doc.getroot()

classPrefix = "platform-"

for element in root.find_class("download"):
    [platform] = [
        cls[len(classPrefix) :]
        for cls in element.classes
        if cls.startswith(classPrefix)
    ]
    [asset] = [
        asset for asset in releaseInfo["assets"] if platform in asset["name"].lower()
    ]
    [anchorElement] = element.iter("a")
    [versionElement] = element.find_class("version")
    [datetimeElement] = element.iter("time")

    anchorElement.set("href", asset["browser_download_url"])
    versionElement.text = releaseInfo["tag_name"]
    datetimeElement.set("datetime", asset["updated_at"])
    datetimeElement.text = asset["updated_at"]

indexPath.write_bytes(lxml.html.tostring(doc, encoding="utf-8") + b"\n")
