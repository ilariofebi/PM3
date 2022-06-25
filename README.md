# PM3
Like pm2 without node.js ;-)

# PM3 CheatSheet:
### Install and update
```
pip install pm3             # Install pm3
pip install -U pm3          # Upgrade pm3
```

### Start
```
pm3 daemon start    # Start process with default ~/.pm3/config.ini configuration 
pm3 ping            # Ensure pm3 daemon has been launched
```


### Create new process
```
pm3 new '/bin/sleep 10' -n sleep10                  # Create a new process with name sleep10
pm3 new '/bin/sleep 10' -n sleep10 --autorun        # Create a new process with autorun option
```
### Actions
```
pm3 start sleep10   # Start process with name sleep10
pm3 start 1         # Start process with id 1
pm3 restart all     # Restart all process
pm3 stop 2          # Stop process with id 2 
pm3 rm 3            # Stop and delete process with id 3
```

### Listing
```
pm3 ls                 # Display all processes
pm3 ls -l              # Display all processes in list format
pm3 ps 5               # Display process 5 status
pm3 ps -l ALL          # Display ALL processes (hidden or not) status in list format
```

### Dump and Load
```
pm3 dump 2                  # Print process 2 configuration in JSON
pm3 dump all -f dump.json   # Save all configuration processes in dump.json file 
pm3 load dump.json          # Load all configuration processes from dump.json file 
```

### Logs
```
pm3 log            # Display all processes logs
pm3 log 5 -f       # Display and follow log of process 5
pm3 err 2 -n 50    # Display last 50 rows of process 5 error log 
```

### Useful script generation
```
pm3 make_script systemd     # Generate script for install startup systemd configuration
pm3 make_script pm3_edit    # Generate script for edit process configuration on the fly 
```


### Misc
```
pm3 reset <process>     # Reset meta data (restarted time...)
pm3 ping                # Ensure pm3 daemon has been launched
pm3 -h                  # General help
pm3 new -h              # Help of new subcommand  
```


## Autocompletition (experimental)
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


