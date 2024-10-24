import os
import pathlib
import markdown
from urllib.request import urlopen


def downloadURL(url):
    print("downloading", url)
    response = urlopen(url)
    data = response.read()
    return data.decode("utf-8")


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
{html}
</body>
</html>
"""


print("Generating html...")

changeLogURL = (
    "https://raw.githubusercontent.com/googlefonts/fontra/refs/heads/main/CHANGELOG.md"
)
markdownSource = downloadURL(changeLogURL)

mdConverter = markdown.Markdown()
htmlIndex = docsDir / "changelog.html"
htmlIndex.write_text(
    htmlTemplate.format(html=mdConverter.convert(markdownSource), encoding="utf-8")
)
