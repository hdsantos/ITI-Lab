# no controlador 192.168.57.10
cd ~/ansible-lab

# 0. base
ansible -i inventory.ini all -m ping

# 1. Docker em todos
ansible-playbook -i inventory.ini 01-install-docker.yml

# 2. Monitoring no controlador
ansible-playbook -i inventory.ini 02-deploy-monitoring.yml

# 3. VERIFICAÇÃO COMPLETA
ansible-playbook -i inventory.ini 99-verify.yml

# Esperado:
# - disk: 8.1G / 3.6G nos nós, 18G / 7.0G no controlador
# - docker: 3x OK
# - exporter 9100: 3x OK
# - prometheus: OK http://192.168.57.10:9090 (3 targets UP)
# - grafana: OK http://192.168.57.10:3000 (admin/admin123)