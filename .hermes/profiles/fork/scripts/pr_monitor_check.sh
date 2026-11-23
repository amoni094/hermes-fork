#!/bin/bash
# PR thread monitor — outputs unresolved thread count + summaries
# Deterministic: only prints counts and thread bodies, no timestamps

OWNER="jesterG1979"
REPO="hello_agent"
PRS="2072 2073 2074"
TOTAL=0

for pr in $PRS; do
  result=$(gh api graphql \
    -f query='query($owner:String!,$repo:String!,$number:Int!){repository(owner:$owner,name:$repo){pullRequest(number:$number){state reviewDecision reviewThreads(first:50){nodes{id isResolved comments(first:1){nodes{body author{login}}}}}}}}' \
    -f owner="$OWNER" \
    -f repo="$REPO" \
    -F number="$pr" 2>/dev/null)

  state=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']['repository']['pullRequest']; print(d['state'])")
  threads=$(echo "$result" | python3 -c "
import sys,json
d=json.load(sys.stdin)['data']['repository']['pullRequest']['reviewThreads']['nodes']
unresolved=[t for t in d if not t['isResolved']]
print(len(unresolved))
for t in unresolved:
    c=t['comments']['nodes'][0]
    print(f\"  THREAD {t['id'][:30]} [{c['author']['login']}]: {c['body'][:120]}\")
")
  count=$(echo "$threads" | head -1)
  TOTAL=$((TOTAL + count))
  echo "PR#$pr state=$state unresolved=$count"
  echo "$threads" | tail -n +2
done

echo "TOTAL_UNRESOLVED=$TOTAL"
