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


pm3_scripts = dict(systemd=_systemd_service)

# TODO: perfezionare il nuovo formato
pm3_scripts_new = dict(systemd={'script': _systemd_service,
                                'description': '',
                                'how_to_install': 'sudo bash {filename}'},
                       )