# PM3
Like pm2 without node.js ;-)

# Install
`pip install pm3`

# Start
`pm3 daemon start`

`pm3 ping`

# Help
`pm3 -h`

# Bash Tools
```commandline
#!/bin/bash

TMPFILE=$(mktemp --suffix=.json)
pm3 dump ${1} -f $TMPFILE
vi $TMPFILE
pm3 load -f $TMPFILE -r
```

## Autocompletition
### Bash
```
pm3_exe=$(which pm3)
eval "$(register-python-argcomplete $pm3_exe)"
```

### Fish
```
pm3_exe=$(which pm3)
register-python-argcomplete --shell fish $pm3_exe | source
```
or
```
register-python-argcomplete --shell fish $pm3_exe > ~/.config/fish/completions/pm3.fish
```

### Other shell
visit https://kislyuk.github.io/argcomplete/


