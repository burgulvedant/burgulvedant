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
 
 
def search(state):
  query = 'query($login:String!){user(login:$login){pullRequests(first:100,states:%s,orderBy:{field:CREATED_AT,direction:DESC}){nodes{number title url createdAt closedAt repository{nameWithOwner owner{login}}}}}}' % state
  body = json.dumps({"query": query, "variables": {"login": USER}}).encode()
  request = urllib.request.Request("https://api.github.com/graphql", data=body)
  request.add_header("Authorization", "Bearer " + os.environ["GITHUB_TOKEN"])
  nodes = json.load(urllib.request.urlopen(request))["data"]["user"]["pullRequests"]["nodes"]
  return [{"number": n["number"], "title": n["title"], "html_url": n["url"], "repository_url": "/repos/" + n["repository"]["nameWithOwner"], "closed_at": n["closedAt"] or "", "created_at": n["createdAt"]} for n in nodes if n["repository"]["owner"]["login"] != USER]
 
 
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
  merged = search("MERGED")
  0opened = search("OPEN")
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

