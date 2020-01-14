#!/bin/sh

# To utilize this git hook, there is a need to specify symbolic link
#   from the place where git is looking for hooks into our location
# sudo ln -s -f ../../git_hooks/pre-commit.bash .git/hooks/pre-commit

python3.8 tests.py
