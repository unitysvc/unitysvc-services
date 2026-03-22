#!/usr/bin/env bash
#
# Run tests for all services, collect failures, and detect false positives
# (tests that report success but contain error messages in stdout).
#
# Usage:
#   ./run_all_tests.sh              # Sequential
#   ./run_all_tests.sh -j 4         # 4 services in parallel
#   ./run_all_tests.sh --no-force   # Skip already-passed tests
#
# Output files (in results_YYYYMMDD_HHMMSS/):
#   failed_tests.csv      - Tests that explicitly failed
#   false_positives.csv   - Tests marked success but with error patterns in stdout
#   run_log.txt           - Full run log
#   summary.txt           - Summary stats
#
set -euo pipefail

# Parse arguments
CONCURRENCY=1
FORCE_FLAG="--force"
while [[ $# -gt 0 ]]; do
    case $1 in
        -j|--concurrency) CONCURRENCY="$2"; shift 2 ;;
        --no-force) FORCE_FLAG=""; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_DIR="results_${TIMESTAMP}"
mkdir -p "$RESULTS_DIR"

FAILED_FILE="$RESULTS_DIR/failed_tests.csv"
FALSE_POS_FILE="$RESULTS_DIR/false_positives.csv"
RUN_LOG="$RESULTS_DIR/run_log.txt"
SUMMARY_FILE="$RESULTS_DIR/summary.txt"

log() {
    echo "$1" | tee -a "$RUN_LOG"
}

log "=== Test Run Started: $(date) ==="
log "Concurrency: $CONCURRENCY"
log ""

# Step 1 & 2: Run all tests
log "Running tests for all services..."
usvc services run-tests --all -j "$CONCURRENCY" $FORCE_FLAG 2>&1 | tee -a "$RUN_LOG"
log ""

# Step 3 & 4: Analyze results in a single bulk fetch using list-tests -v
log "Analyzing test results (single bulk fetch)..."

# One call gets everything: status, exit_code, stdout, stderr for all tests
usvc services list-tests -v -f json 2>&1 | python3 -c "
import sys, json, re

data = json.loads(sys.stdin.read(), strict=False)

failed_file = '$FAILED_FILE'
false_pos_file = '$FALSE_POS_FILE'
run_log = '$RUN_LOG'
summary_file = '$SUMMARY_FILE'

def log(msg):
    print(msg)
    with open(run_log, 'a') as f:
        f.write(msg + '\n')

def csv_quote(s):
    s = str(s).replace('\"', '\"\"')
    return f'\"{s}\"' if (',' in s or '\"' in s or '\n' in s) else s

error_patterns = [
    (r'(?i)\berror\s+4\d{2}\b', 'HTTP 4xx error'),
    (r'(?i)\berror\s+5\d{2}\b', 'HTTP 5xx error'),
    (r'(?i)\"error\"', 'JSON error field'),
    (r'(?i)\b404\s+not\s+found\b', '404 Not Found'),
    (r'(?i)\b403\s+forbidden\b', '403 Forbidden'),
    (r'(?i)\b401\s+unauthorized\b', '401 Unauthorized'),
    (r'(?i)\b500\s+internal\s+server\b', '500 Internal Server Error'),
    (r'(?i)\b502\s+bad\s+gateway\b', '502 Bad Gateway'),
    (r'(?i)\b503\s+service\s+unavailable\b', '503 Service Unavailable'),
    (r'(?i)connection\s+refused', 'Connection refused'),
    (r'(?i)connection\s+timed?\s*out', 'Connection timeout'),
    (r'(?i)traceback\s*\(most\s+recent', 'Python traceback'),
    (r'(?i)ECONNREFUSED', 'ECONNREFUSED'),
    (r'(?i)ETIMEDOUT', 'ETIMEDOUT'),
    (r'(?i)invalid_request_error', 'Invalid request error'),
    (r'(?i)authentication_error', 'Authentication error'),
    (r'(?i)rate_limit_error', 'Rate limit error'),
    (r'(?i)\"type\":\s*\"error\"', 'Error type in response'),
]

# CSV headers
with open(failed_file, 'w') as f:
    f.write('service_name,service_id,doc_id,title,interface,status,exit_code,stdout,stderr\n')
with open(false_pos_file, 'w') as f:
    f.write('service_name,service_id,doc_id,title,interface,status,exit_code,error_pattern,stdout_snippet\n')

total = len(data)
total_failed = 0
total_false_positives = 0
total_success = 0
total_pending = 0
services_with_issues = set()

for t in data:
    svc_name = t.get('service_name', '')
    svc_id = t.get('service_id', '')
    doc_id = t.get('doc_id', '')
    title = t.get('title', '')
    interface = t.get('interface', '')
    status = t.get('status', 'pending')
    exit_code = t.get('exit_code', '')
    stdout = t.get('stdout', '')
    stderr = t.get('stderr', '')

    if status == 'pending':
        total_pending += 1
        continue

    if status not in ('success', 'pending', 'skip'):
        total_failed += 1
        services_with_issues.add(svc_id)
        with open(failed_file, 'a') as f:
            f.write(f'{csv_quote(svc_name)},{csv_quote(svc_id)},{csv_quote(doc_id)},{csv_quote(title)},{csv_quote(interface)},{csv_quote(status)},{exit_code},{csv_quote(stdout)},{csv_quote(stderr)}\n')
        log(f'  FAILED: [{svc_name}] {title} ({interface}) [doc: {doc_id}]')
        continue

    if status == 'success':
        total_success += 1
        combined = (stdout or '') + (stderr or '')
        for pattern, label in error_patterns:
            m = re.search(pattern, combined)
            if m:
                start = max(0, m.start() - 40)
                end = min(len(combined), m.end() + 40)
                snippet = combined[start:end].replace('\n', ' ')
                total_false_positives += 1
                services_with_issues.add(svc_id)
                with open(false_pos_file, 'a') as f:
                    f.write(f'{csv_quote(svc_name)},{csv_quote(svc_id)},{csv_quote(doc_id)},{csv_quote(title)},{csv_quote(interface)},success,{exit_code},{csv_quote(label)},{csv_quote(snippet)}\n')
                log(f'  FALSE POSITIVE: [{svc_name}] {title} ({interface}) - {label} [doc: {doc_id}]')
                break

log('')
from datetime import datetime
summary = f'''=== Test Run Summary ===
Date: {datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}
Total test results: {total}
  Success: {total_success}
  Failed: {total_failed}
  Pending: {total_pending}
  False positives (pass with errors in stdout): {total_false_positives}
Services with issues: {len(services_with_issues)}

Output files:
  Failed tests:      {failed_file}
  False positives:   {false_pos_file}'''

log(summary)
with open('$SUMMARY_FILE', 'w') as f:
    f.write(summary)
"

echo ""
echo "Done. Results saved in $RESULTS_DIR/"
