import json
import lxml.html
import os
import re
import pathlib
import markdown
from release_info import downloadResource, getReleaseInfo
from urllib.request import urlopen


docsDir = pathlib.Path(__file__).resolve().parent.parent / "docs"


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


indentPat = re.compile(r"^( +)")


def doubleIndentation(source):
    lines = []
    for line in source.splitlines():
        if line:
            line = indentPat.sub(r"\1\1", line)
        lines.append(line)
    return "\n".join(lines)


htmlTemplate = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fontra — Latest Changes</title>
<link rel="stylesheet" href="changelog.css">
</style>
</head>
<body>
<a href="https://fontra.xyz"><img class="icon" src="./fontra-icon.svg" /></a>
{mdHtml}
</body>
</html>
"""

changeLogURLTemplate = "https://raw.githubusercontent.com/fontra/fontra/refs/tags/{releaseTag}/CHANGELOG.md"


def updateChangeLog(releaseTag):
    changeLogURL = changeLogURLTemplate.format(releaseTag=releaseTag)

    markdownSource = downloadResource(changeLogURL)
    markdownSource = doubleIndentation(markdownSource)

    mdConverter = markdown.Markdown()
    mdHtml = mdConverter.convert(markdownSource)

    outPath = docsDir / "changelog.html"
    outPath.write_text(htmlTemplate.format(mdHtml=mdHtml, encoding="utf-8"))


def updateDownloadInfo(releaseInfo):
    indexPath = docsDir / "index.html"
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



if __name__ == "__main__":
    releaseInfo = getReleaseInfo()
    updateChangeLog(releaseInfo["tag_name"])
    updateDownloadInfo(releaseInfo)
