import os
import re
import pathlib
import markdown
from release_info import downloadResource, getReleaseInfo
from urllib.request import urlopen


indentPat = re.compile(r"^( +)")


def doubleIndentation(source):
    lines = []
    for line in source.splitlines():
        if line:
            line = indentPat.sub(r"\1\1", line)
        lines.append(line)
    return "\n".join(lines)


thisDir = pathlib.Path(__file__).resolve().parent
docsDir = thisDir.parent / "docs"

releaseInfo = getReleaseInfo()
releaseTag = releaseInfo["tag_name"]

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


print("Generating html...")

changeLogURL = f"https://raw.githubusercontent.com/fontra/fontra/refs/tags/{releaseTag}/CHANGELOG.md"

markdownSource = downloadResource(changeLogURL)
markdownSource = doubleIndentation(markdownSource)

mdConverter = markdown.Markdown()
mdHtml = mdConverter.convert(markdownSource)

outPath = docsDir / "changelog.html"
outPath.write_text(htmlTemplate.format(mdHtml=mdHtml, encoding="utf-8"))
