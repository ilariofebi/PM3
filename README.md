# PM3
Like pm2 without node.js ;-)

# Install
`pip install pm3`

# Start
`pm3 daemon start`

`pm3 ping`

# Help
`pm3 -h`

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


