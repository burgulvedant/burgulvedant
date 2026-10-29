"""Rewrites the open source section of README.md from live GitHub data."""
 
import datetime
import json
import os
import re
import urllib.error
import urllib.request
 
USER = "burgulvedant"
GOAL = 50
BAR_WIDTH = 21
START = "<!-- OSS:START -->"
END = "<!-- OSS:END -->"
TRACKED = re.compile(r"<!-- OSS:TRACKED (.*?) -->")
 
# GitHub owner (lowercase) to the company name shown in the README.
COMPANY = {
    "amd": "AMD",
    "apple": "Apple",
    "google": "Google",
    "googleapis": "Google",
    "facebook": "Meta",
    "facebookresearch": "Meta",
    "meta-llama": "Meta",
    "nvidia": "NVIDIA",
    "microsoft": "Microsoft",
    "openai": "OpenAI",
    "anthropics": "Anthropic",
    "anthropic": "Anthropic",
    "aws": "Amazon/AWS",
    "awslabs": "Amazon/AWS",
    "aws-samples": "Amazon/AWS",
}
 
# Companies I am aiming at. Any with no PR yet are listed in the last table row.
TARGETS = ["Apple", "Google", "Meta", "NVIDIA", "Microsoft", "OpenAI", "Anthropic", "Amazon/AWS"]
 
 
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
 
 
def owner(item):
    return item["repo"].split("/")[0]
 
 
def company(item):
    return COMPANY.get(owner(item).lower(), owner(item))
 
 
def cell(text):
    """Make text safe inside a markdown table cell."""
    return text.replace("|", "\\|").replace("\n", " ")
 
 
def pr_row(item):
    return "| [%s](https://github.com/%s) | [#%d](%s) | %s |" % (
        item["repo"],
        item["repo"],
        item["number"],
        item["url"],
        cell(item["title"]),
    )
 
 
def pr_table(items, empty_text):
    if not items:
        return [empty_text]
    lines = ["| Repo | PR | Title |", "| --- | --- | --- |"]
    lines += [pr_row(i) for i in items]
    return lines
 
 
def org_rows(merged, opened):
    """One row per company, most merged first."""
    groups = {}
    for item in merged + opened:
        groups.setdefault(company(item), []).append(item)
    rows = []
    for name, items in groups.items():
        n_merged = sum(1 for i in items if i["merged"])
        n_open = sum(1 for i in items if i["state"] == "open")
        repos = sorted({i["repo"].split("/")[1] for i in items})
        rows.append((name, n_merged, n_open, repos, items[0]["repo"]))
    rows.sort(key=lambda r: (-r[1], -r[2], r[0].lower()))
    return rows
 
 
def render(merged, opened, tracked, today):
    n = len(merged)
    filled = min(BAR_WIDTH, round(BAR_WIDTH * n / GOAL))
    bar = "\u2588" * filled + "\u2591" * (BAR_WIDTH - filled)
    percent = round(100 * n / GOAL)
    remaining = max(0, GOAL - n)
 
    lines = [
        START,
        "**%d / %d merged** as of %s (Asia/Calcutta), with **%d open**."
        % (n, GOAL, today, len(opened)),
        "Only PRs to other people's repos are listed. My own repos are not included.  ",
        "Aiming at Apple, Google, Meta, NVIDIA, Microsoft, OpenAI, Anthropic and Amazon/AWS."
        "  ",
        "**%d more to reach %d.**" % (remaining, GOAL),
        "",
        "```text",
        "%d / %d  %s  %d%%" % (n, GOAL, bar, percent),
        "```",
        "",
        "### By organization",
        "",
        "| Org | Merged | Open | Repos |",
        "| --- | ---: | ---: | --- |",
    ]
    seen = set()
    for name, n_merged, n_open, repos, first_repo in org_rows(merged, opened):
        seen.add(name)
        lines.append(
            "| [%s](https://github.com/%s) | %d | %d | %s |"
            % (name, first_repo, n_merged, n_open, cell(", ".join(repos)))
        )
    missing = [t for t in TARGETS if t not in seen]
    if missing:
        lines.append("| %s | 0 | 0 | none yet |" % " \u00b7 ".join(missing))
    lines += ["", "### Merged", ""]
    lines += pr_table(merged, "None yet.")
    lines += ["", "### Open", ""]
    lines += pr_table(opened, "None right now.")
    lines += [
        "",
        "[**See all merged PRs \u2192**](https://github.com/search?q=is%3Apr+author%3A"
        + USER
        + "+is%3Amerged+-user%3A"
        + USER
        + "&type=pullrequests)",
        "",
        "<!-- OSS:TRACKED %s -->" % " ".join(sorted(tracked)),
        END,
    ]
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
    ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    today = datetime.datetime.now(ist).date().isoformat()
    block = render(merged, opened, tracked, today)
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(pattern.sub(lambda _: block, text))
 
 
if __name__ == "__main__":
    main()
