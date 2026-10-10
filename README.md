# Public CI Bridge (prototype)

Project-agnostic public GitHub Actions workers for approved private source repositories. **Local prototype: not security-certified or ready to publish.**

## Design
- The public worker keeps a trust-controlled allowlist in `projects/<id>.json`.
- Only project ID and immutable commit SHA are accepted from dispatch requests.
- A GitHub App installation provides short-lived read-only access to private source.
- The matrix runs Windows and Linux; build instructions are argv arrays rather than shell snippets.
- No source, logs, or build objects are uploaded as public artifacts or caches.
- Authentication and trust restrictions must be completed **before** any production deployment.

## Setup to finish
1. Create a separate GitHub App with Contents: read restricted to specifically authorized private repos. Install only on those repos. The App secret in the public worker will still be available to a compromised workflow; restrict who can change the workflow and project files.
2. Set Actions secrets `SOURCE_APP_ID` and `SOURCE_APP_PRIVATE_KEY`, and variable `SOURCE_OWNER` in the worker repository. Note that public repository Actions editors can modify workflows and exfiltrate secrets; restrict write access and review changes.
3. Register project configurations in `projects/` (trusted, reviewed changes only). Build scripts in a checked-out source repo are untrusted code and can read the short-lived clone token and credentials unless isolation is implemented.
4. Implement dispatch authentication, check-result reporting back to private repo, PR check behavior, and secure credential separation **before enabling**. A separate read-only checkout job must prepare source for isolated build jobs without secrets, using a safe transfer mechanism; do not run source-controlled builds in the credential-bearing job.
5. Do not accept untrusted fork PRs, expose cache entries containing private data, or publish binaries/debug symbols/artifacts unless reviewed.

## Local tests
`python3 -m unittest discover -s tests -v`

## Security status
The current workflow is **NOT SAFE FOR PRIVATE-SOURCE BUILDS** because checkout and build run in the same job with a privileged short-lived GitHub App token. This is a scaffold only. The checkout step also requires `SOURCE_OWNER` passed as an environment variable. Do not activate the workflow until these issues are addressed.
