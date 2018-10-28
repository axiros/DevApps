# Writing the test_tutorial.py

```
find test_tutorial.py | entr sh -c 'pytest -vv test_tutorial.py '
```

will render tutorial.md (as part of the testrunning)  on change.

Open vscode to see it live updated.

On breakpoints the renderer will stop normally.
