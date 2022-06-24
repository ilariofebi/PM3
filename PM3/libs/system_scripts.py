_systemd_service = '''#!/bin/bash

cat << EOF > /etc/systemd/system/pm3.service
[Unit]
Description=PM3 Backend
After=network.target

[Service]
User={}
Type=simple
ExecStart={}
Restart=always

[Install]
WantedBy=multi-user.target
EOF
echo 'file /etc/systemd/system/pm3.service written'

echo 'systemctl daemon-reload'
systemctl daemon-reload

echo 'systemctl enable pm3'
systemctl enable pm3

echo 'systemctl start pm3'
systemctl start pm3
systemctl is-active pm3
'''

pm3_scripts = dict(systemd=_systemd_service)