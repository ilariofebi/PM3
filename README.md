# PM3
Like pm2 without node.js ;-)
![](https://github.com/ilariofebi/PM3/blob/main/screenshots/ls.png?raw=true)
# PM3 CheatSheet:
### Install and update
Build a [virtualenv](https://docs.python.org/3.9/tutorial/venv.html) environment (recommended)
```
python3.9 -m venv PM3venv
. PM3venv/bin/activate
```
Then:
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
pm3 new '/bin/sleep 10' -n sleep10                                  # Create a new process with name sleep10
pm3 new '/bin/sleep 10' -n sleep10 --autorun                        # Create a new process with autorun option
pm3 new "script.py" --interpreter "/venv/bin/python" --cwd "/tmp"   # Create a new process with interpreter and cwd definition
pm3 new '/bin/sleep 5' --max-restart 10 --autorun                   # Stops restarting the process after 10 restarts        
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
pm3 flush 1 log    # Empty log file of process 1
pm3 flush all err  # Empty err file of all process
```

### Useful script generation
```
pm3 make_script systemd     # Generate script for install startup systemd configuration
pm3 make_script pm3_edit    # Generate script for edit process configuration on the fly 
```

### Misc
```
pm3 reset 2                 # Reset meta data of process id 2
pm3 ping [-v]               # Ensure pm3 daemon has been launched [verbose]
pm3 rename 3 -n <new_name>  # Rename process id 3 with a <new_name>
pm3 -h                      # General help
pm3 new -h                  # Help of new subcommand  
```

### Daemon commands
```
pm3 daemon start        # Start PM3 backend porcess
pm3 daemon stop         # Stop PM3 backend porcess
pm3 daemon status       # Check daemon status details
```

# Configuration file:
`$ cat ~/.pm3/config.ini`
```
[main_section]
pm3_home_dir = /home/user/.pm3                  # pm3 home dir
pm3_db = /home/user/.pm3/pm3_db.json            # TinyDB Store File
pm3_db_process_table = pm3_procs                # TinyDB process table
main_interpreter = /home/user/venv/bin/python   # path of python interpreter

[backend]
name = __backend__                       # name of backend process (hidden process)
url = http://127.0.0.1:7979/             # proto://ip:port of backend (if != 127.1 is a potential RISK!!)
cmd = /home/user/venv/bin/pm3_backend    # path of backend command

[cron_checker]
name = __cron_checker__                      # name of backend process (hidden process)
cmd = /home/user/venv/bin/pm3_cron_checker   # path of cron checker command
sleep_time = 5                               # Time (in seconds) to check process                            
debug = False                                # Crocn Checker debug info
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


