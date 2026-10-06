import datetime
import email.utils
import xml.etree.ElementTree as ET
import json
import lxml.html
import re
import pathlib
import markdown
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


# "2026-09-29 [version 2026.9.2]", optionally already a heading or bold
versionLinePat = re.compile(
    r"^(?:#+\s*|\*\*|__)?\s*"
    r"(\d{4}-\d{2}-\d{2}\s+\[version\s+([^\]]+)\])"
    r"\s*(?:\*\*|__)?\s*$",
    re.IGNORECASE,
)


def addVersionAnchors(source):
    # "## [2026-09-29 \[version 2026.9.2\]](#2026.9.2) {#2026.9.2}"
    lines = []
    for line in source.splitlines():
        match = versionLinePat.match(line)
        if match:
            if lines and lines[-1].strip():
                lines.append("")  # a heading needs a blank line before it
            text = match.group(1).replace("[", r"\[").replace("]", r"\]")
            version = match.group(2).strip()
            line = f"## [{text}](#{version}) {{#{version}}}"
        lines.append(line)
    return "\n".join(lines)


siteURL = "https://fontra.xyz"
maxFeedEntries = 20
atomNS = "http://www.w3.org/2005/Atom"
ET.register_namespace("atom", atomNS)


def splitEntries(source):
    # -> [(date, version, markdownBody), ...], newest first
    entries = []
    for line in source.splitlines():
        match = versionLinePat.match(line)
        if match:
            date = match.group(1)[:10]  # "2026-09-29"
            version = match.group(2).strip()
            entries.append((date, version, []))
        elif line.startswith("## "):
            break  # older, date-only entries: no version, no feed item
        elif entries:
            entries[-1][2].append(line)
    return [(date, version, "\n".join(body)) for date, version, body in entries]


def updateFeed(source):
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "Fontra — Latest Changes"
    ET.SubElement(channel, "link").text = f"{siteURL}/changelog.html"
    ET.SubElement(channel, "description").text = "Latest changes in Fontra"
    ET.SubElement(
        channel,
        f"{{{atomNS}}}link",
        href=f"{siteURL}/changelog-feed.xml",
        rel="self",
        type="application/rss+xml",
    )

    for date, version, body in splitEntries(source)[:maxFeedEntries]:
        link = f"{siteURL}/changelog.html#{version}"
        published = datetime.datetime.strptime(date, "%Y-%m-%d").replace(
            tzinfo=datetime.timezone.utc
        )
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = f"Fontra {version}"
        ET.SubElement(item, "link").text = link
        ET.SubElement(item, "guid").text = link
        ET.SubElement(item, "pubDate").text = email.utils.format_datetime(published)
        ET.SubElement(item, "description").text = markdown.markdown(
            doubleIndentation(body)
        )

    ET.indent(rss)
    ET.ElementTree(rss).write(
        docsDir / "changelog-feed.xml", encoding="utf-8", xml_declaration=True
    )


htmlTemplate = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fontra — Latest Changes</title>
<link rel="alternate" type="application/rss+xml" title="Fontra changes" href="changelog-feed.xml">
<link rel="stylesheet" href="changelog.css">
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
    updateFeed(markdownSource)
    markdownSource = addVersionAnchors(markdownSource)
    markdownSource = doubleIndentation(markdownSource)

    mdConverter = markdown.Markdown(extensions=["attr_list"])
    mdHtml = mdConverter.convert(markdownSource)

    outPath = docsDir / "changelog.html"
    outPath.write_text(htmlTemplate.format(mdHtml=mdHtml), encoding="utf-8")


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
