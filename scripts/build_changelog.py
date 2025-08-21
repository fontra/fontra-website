import os
import re
import pathlib
import markdown
from urllib.request import urlopen


def downloadURL(url):
    print("downloading", url)
    response = urlopen(url)
    data = response.read()
    return data.decode("utf-8")


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
<img class="icon" src="./fontra-icon.svg" />
{mdHtml}
</body>
</html>
"""


print("Generating html...")

changeLogURL = (
    "https://raw.githubusercontent.com/fontra/fontra/refs/heads/main/CHANGELOG.md"
)
markdownSource = downloadURL(changeLogURL)
markdownSource = doubleIndentation(markdownSource)

mdConverter = markdown.Markdown()
mdHtml = mdConverter.convert(markdownSource)

outPath = docsDir / "changelog.html"
outPath.write_text(htmlTemplate.format(mdHtml=mdHtml, encoding="utf-8"))
