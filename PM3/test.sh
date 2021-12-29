#!/bin/bash

./cli.py ping
./cli.py ls

./cli.py rm all
./cli.py ls

./cli.py new ls
./cli.py new ./asd
./cli.py new ./asd
./cli.py ls

./cli.py rm 1
./cli.py rm ls
./cli.py rm asd
./cli.py ls