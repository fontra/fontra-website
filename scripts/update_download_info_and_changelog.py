import datetime
import json
import pathlib
import re
from urllib.request import urlopen
from lxml import etree
import lxml.html
import markdown


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


def atomTag(name):
    return f"{{{atomNS}}}{name}"


def updateFeed(source):
    # Atom feed, styled by the same pretty-atom-feed.xsl as the blog feed
    feed = etree.Element(atomTag("feed"), nsmap={None: atomNS})
    etree.SubElement(feed, atomTag("title")).text = "Fontra — Latest Changes"
    etree.SubElement(feed, atomTag("subtitle")).text = "Latest changes in Fontra"
    etree.SubElement(
        feed,
        atomTag("link"),
        href=f"{siteURL}/changelog-feed.xml",
        rel="self",
    )
    etree.SubElement(feed, atomTag("link"), href=f"{siteURL}/changelog.html")
    updatedElement = etree.SubElement(feed, atomTag("updated"))
    etree.SubElement(feed, atomTag("id")).text = f"{siteURL}/changelog.html"
    author = etree.SubElement(feed, atomTag("author"))
    etree.SubElement(author, atomTag("name")).text = "Fontra Team"

    entries = splitEntries(source)[:maxFeedEntries]
    updatedDates = []
    for date, version, body in entries:
        link = f"{siteURL}/changelog.html#{version}"
        updated = datetime.datetime.strptime(date, "%Y-%m-%d").replace(
            tzinfo=datetime.timezone.utc
        )
        updatedDates.append(updated)
        entry = etree.SubElement(feed, atomTag("entry"))
        etree.SubElement(entry, atomTag("title")).text = f"Fontra {version}"
        etree.SubElement(entry, atomTag("link"), href=link)
        etree.SubElement(entry, atomTag("updated")).text = updated.strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        etree.SubElement(entry, atomTag("id")).text = link
        content = etree.SubElement(entry, atomTag("content"), type="html")
        content.text = markdown.markdown(doubleIndentation(body))

    # The feed's <updated> is the newest entry date (the entries are newest first)
    newest = max(updatedDates, default=datetime.datetime.now(datetime.timezone.utc))
    updatedElement.text = newest.strftime("%Y-%m-%dT%H:%M:%SZ")

    # The processing instruction goes into the prolog, before the root element
    pi = etree.ProcessingInstruction(
        "xml-stylesheet", 'type="text/xsl" href="pretty-atom-feed.xsl"'
    )
    feed.addprevious(pi)

    etree.ElementTree(feed).write(
        docsDir / "changelog-feed.xml",
        encoding="utf-8",
        xml_declaration=True,
        pretty_print=True,
    )


htmlTemplate = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fontra — Latest Changes</title>
<link rel="alternate" type="application/atom+xml" title="Fontra changes" href="changelog-feed.xml">
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
