# PM3
Like pm2 without node.js ;-)

# Install
`pip install pm3`

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


## TODO
- sarebbe bello poter inserire piu' id insieme: Es: pm3 rm 1 2 3
- I log e gli err non si vedono, sembra un problema di flushing, forse si risolve con popen.communicate
  - eventualmente inserire nel cron o nel tail