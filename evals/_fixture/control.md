Any change to a path under risk.paths in .claude/funnel.config.json needs a spec the user approved before any code is written.
Before saying a change is done, run every gate in .claude/funnel.config.json and report each result.
Never push to the base branch named in .claude/funnel.config.json.
A bug fix starts with a test that fails because of the bug.
Fix a bug where it lives, in the shared function, not in one of its callers.
