cd ~/ansible-lab
# ou onde clonaste o repo

ansible -i inventory.ini docker_nodes -m ping
# tem de dar pong nos dois

# Instala Docker
ansible-playbook -i inventory.ini 01-install-docker.yml

# Valida
ansible -i inventory.ini docker_nodes -a "docker ps"

# Deploy monitoring (só depois do Docker estar OK)
ansible-playbook -i inventory.ini 02-deploy-monitoring.yml