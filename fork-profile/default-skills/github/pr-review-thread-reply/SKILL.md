---
name: pr-review-thread-reply
version: 1.0.0
author: Hermes Agent
description: "Use when replying to open GitHub PR review threads in bulk."
keywords:
- pr
- review
- threads
- graphql
- reply
- github
platforms:
- linux
---

# PR Review Thread Bulk Reply

Use when you have multiple open reviewer threads across several PRs and need to reply
to all of them efficiently with specific responses per thread.

## Step 1: Fetch all thread IDs and bodies

```python
import subprocess, json

def get_threads(pr_num, owner, repo):
    q = '''
  query($owner:String!,$repo:String!,$number:Int!){
    repository(owner:$owner,name:$repo){
      pullRequest(number:$number){
        reviewThreads(first:50){
          nodes{
            id
            isResolved
            comments(first:3){ nodes{ body author{login} } }
          }
        }
      }
    }
  }'''
    r = subprocess.run(
        ['gh','api','graphql','-f',f'query={q}',
         '-f',f'owner={owner}','-f',f'repo={repo}','-F',f'number={pr_num}'],
        capture_output=True, text=True
    )
    d = json.loads(r.stdout)
    return d['data']['repository']['pullRequest']['reviewThreads']['nodes']
```

## Step 2: Build the REPLIES dict

Map thread_id -> (pr_num, reply_body). Read each thread body to write a targeted reply.
Reply body format: `"Fixed in <sha>. <what changed> -- <why it was wrong>."`

Include the commit SHA so the reviewer can verify without re-reading the diff.

```python
REPLIES = {
    "PRRT_kwDOxxx": (2027, "Fixed in bb9d0a3. Removed value_range multiplier -- W1 is already in ms units."),
    "PRRT_kwDOyyy": (2028, "Fixed in bb9d0a3. Preferred extensions now collect-all-then-maximal-filter; mid-search pruning removed."),
}
```

## Step 3: Send all replies in one script

```python
def reply_to_thread(thread_id, pr_num, body):
    q = '''mutation($threadId:ID!, $body:String!) {
      addPullRequestReviewThreadReply(
        input:{pullRequestReviewThreadId:$threadId, body:$body}
      ) {
        comment { id }
      }
    }'''
    r = subprocess.run(
        ['gh','api','graphql',
         '-f',f'query={q}',
         '-f',f'threadId={thread_id}',
         '-f',f'body={body}'],
        capture_output=True, text=True
    )
    d = json.loads(r.stdout)
    if 'errors' in d:
        print(f"ERROR {thread_id}: {d['errors']}")
    else:
        print(f"OK {thread_id} (PR #{pr_num})")

for tid, (pr_num, body) in REPLIES.items():
    reply_to_thread(tid, pr_num, body)
```

## Pitfalls

- `gh pr view --comments` shows only top-level conversation comments. Inline reviewer
  threads require the `reviewThreads` GraphQL query -- always run both.
- The mutation name is `addPullRequestReviewThreadReply` (not `addComment` or
  `addPullRequestReviewComment`). Using the wrong mutation silently fails or creates
  a top-level comment instead of a threaded reply.
- Skip bot-authored threads (automated diagram bots, CI reporters). Only human or LLM
  reviewer inline threads are actionable. Check `author.login` to distinguish.
- Run `isResolved` check -- skip threads already resolved to avoid redundant replies.
