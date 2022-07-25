_systemd_service = '''#!/bin/bash

cat << EOF > /etc/systemd/system/pm3_{USER}.service
[Unit]
Description=PM3 ({USER}) Backend
After=network.target

[Service]
User={USER}
Type=simple
ExecStart={EXE}
Restart=always

[Install]
WantedBy=multi-user.target
EOF
echo 'file /etc/systemd/system/pm3_{USER}.service written'

echo 'systemctl daemon-reload'
systemctl daemon-reload

echo 'systemctl enable pm3_{USER}'
systemctl enable pm3_{USER}

echo 'systemctl start pm3_{USER}'
systemctl start pm3_{USER}
systemctl is-active pm3_{USER}
'''

_pm3_edit = '''#!/bin/bash
# Useful script for edit process in indented json format
#Use: pm3_edit.sh <id or process name>

if (( $# != 1 )); then
    >&2 echo "Use: pm3_edit.sh <id or process name>"
    exit 1
fi

EDITOR=$(which nano || which pico || which vim || which vi || wichi emacs)

TMPFILE=$(mktemp --suffix=.json)

pm3 dump ${1} -f $TMPFILE
$EDITOR $TMPFILE
pm3 load -f $TMPFILE -r
'''

pm3_scripts = dict(systemd=_systemd_service,
                   pm3_edit=_pm3_edit)

# TODO: perfezionare il nuovo formato
pm3_scripts_new = dict(systemd={'script': _systemd_service,
                                'description': '',
                                'how_to_install': 'sudo bash {filename}'},
                       pm3_edit={'script': _pm3_edit,
                                 'description': '',
                                 'how_to_install': 'chmod 755 {filename}',
                                 'how_to_use': './{filename} <id_or_name>'},
                       )