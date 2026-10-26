"""Rewrites the open source section of README.md from live GitHub data."""
 
import datetime
import json
import os
import re
import urllib.parse
import urllib.request
 
USER = "burgulvedant"
GOAL = 50
START = "<!-- OSS:START -->"
END = "<!-- OSS:END -->"
 
 
def search(query):
  """Returns every issue or PR matching a GitHub search query."""
  items = []
  page = 1
  while True:
    url = (
        "https://api.github.com/search/issues?per_page=100&page=%d&q=%s"
        % (page, urllib.parse.quote(query))
    )
    request = urllib.request.Request(url)
    request.add_header("Accept", "application/vnd.github+json")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
      request.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(request) as response:
      data = json.load(response)
    items.extend(data["items"])
    if len(data["items"]) < 100:
      return items
    page += 1
 
 
def repo_name(item):
  return item["repository_url"].split("/repos/")[1]
 
 
def bullet(item):
  return "- **%s:** [#%d %s](%s)" % (
      repo_name(item),
      item["number"],
      item["title"],
      item["html_url"],
  )
 
 
def render(merged, opened, today):
  lines = [
      START,
      "**%d merged and %d open upstream PRs** as of %s. Only PRs to other"
      " people's repos are listed. My own repos are not included."
      % (len(merged), len(opened), today),
      "",
      "**Goal: %d merged PRs.** Progress: %d / %d (%d percent)."
      % (GOAL, len(merged), GOAL, round(100 * len(merged) / GOAL)),
      "",
      "### Merged",
      "",
  ]
  lines += [bullet(i) for i in merged] or ["None yet."]
  lines += ["", "### Open", ""]
  lines += [bullet(i) for i in opened] or ["None right now."]
  lines += ["", END]
  return "\n".join(lines)
 
 
def main():
  base = "author:%s is:pr -user:%s " % (USER, USER)
  merged = search(base + "is:merged")
  opened = search(base + "is:open")
  merged.sort(key=lambda i: i["closed_at"], reverse=True)
  opened.sort(key=lambda i: i["created_at"], reverse=True)
  today = datetime.date.today().isoformat()
  block = render(merged, opened, today)
  with open("README.md", encoding="utf-8") as f:
    text = f.read()
  pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
  if not pattern.search(text):
    raise SystemExit("Markers not found in README.md")
  with open("README.md", "w", encoding="utf-8") as f:
    f.write(pattern.sub(lambda _: block, text))
 
 
if __name__ == "__main__":
  main()
 
Claude finished the respons
