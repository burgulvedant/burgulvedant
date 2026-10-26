"""Rewrites the open source section of README.md from live GitHub data."""

import datetime
import json
import os
import re
import urllib.error
import urllib.request

USER = "burgulvedant"
GOAL = 50
START = "<!-- OSS:START -->"
END = "<!-- OSS:END -->"
TRACKED = re.compile(r"<!-- OSS:TRACKED (.*?) -->")


def api(path):
    request = urllib.request.Request("https://api.github.com" + path)
    request.add_header("Accept", "application/vnd.github+json")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def discover():
    """PRs opened on other people's repos, from the public events feed."""
    found = set()
    for page in (1, 2, 3):
        events = api("/users/%s/events/public?per_page=100&page=%d" % (USER, page))
        for event in events:
            if event["type"] != "PullRequestEvent":
                continue
            repo = event["repo"]["name"]
            if repo.split("/")[0].lower() == USER.lower():
                continue
            found.add("%s#%d" % (repo, event["payload"]["number"]))
        if len(events) < 100:
            break
    return found


def fetch(key):
    """The current state of one tracked PR, or None if it is not mine or is gone."""
    repo, number = key.split("#")
    try:
        pr = api("/repos/%s/pulls/%s" % (repo, number))
    except urllib.error.HTTPError:
        return None
    if pr["user"]["login"].lower() != USER.lower():
        return None
    return {
        "repo": repo,
        "number": pr["number"],
        "title": pr["title"],
        "url": pr["html_url"],
        "state": pr["state"],
        "merged": bool(pr["merged_at"]),
        "closed_at": pr["closed_at"] or "",
        "created_at": pr["created_at"],
    }


def bullet(item):
    return "- **%s:** [#%d %s](%s)" % (
        item["repo"],
        item["number"],
        item["title"],
        item["url"],
    )


def render(merged, opened, tracked, today):
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
    lines += ["", "<!-- OSS:TRACKED %s -->" % " ".join(sorted(tracked)), END]
    return "\n".join(lines)


def main():
    with open("README.md", encoding="utf-8") as f:
        text = f.read()
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        raise SystemExit("Markers not found in README.md")
    previous = TRACKED.search(text)
    tracked = set(previous.group(1).split()) if previous else set()
    tracked |= discover()
    items = [i for i in (fetch(key) for key in sorted(tracked)) if i]
    merged = [i for i in items if i["merged"]]
    opened = [i for i in items if i["state"] == "open"]
    merged.sort(key=lambda i: i["closed_at"], reverse=True)
    opened.sort(key=lambda i: i["created_at"], reverse=True)
    today = datetime.date.today().isoformat()
    block = render(merged, opened, tracked, today)
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(pattern.sub(lambda _: block, text))


if __name__ == "__main__":
    main()
