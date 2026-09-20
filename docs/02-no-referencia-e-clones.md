# Lab Ansible + Docker + Monitoring - Parte 2: Nó de Referência e Clones

Guia para criar a _golden image minimized_ (1 vCPU / 2GB / 10GB de disco) e clonar para node1/node2.
Testado em Ubuntu Server 26.04.1 Resolute + VirtualBox 7.x.

## 1. Porquê Minimized?

O ISO é o mesmo do controlador e os passos a seguir, bem como a configuração inicial, são semelhantes. Durante a instalação escolher a opção **Minimized**.
Diferenças vs normal:
- Sem `nano`, sem `netplan` (comando), sem `iputils-ping`
- Sem `cloud-init` a fazer wait de 2 min no boot (arranca em cerca de 10s)
- Disco final: 8.1G com 3.6G usados vs 18G do controlador

## 2. Criar VM `iti-no` (modelo)

*   Nova VM: `iti-no` / 1 vCPU / 2048 MB RAM / 10 GB disco
*   Rede:
    *   Adapter 1: Bridged (para internet, inicialmente)
    *   Adapter 2: Host-only `192.168.57.1/24` (SEM DHCP)
*   System > Processor:
    *   Enable PAE/NX: ON
    *   Enable Nested Paging: ON
    *   Nested VT-x: OFF
    *   Paravirt: KVM
*   ISO: Ubuntu Server 26.04.1
*   **Desmarcar `Unattended Installation`**
*   Tipo de instalação: **Minimized** (quando o instalador perguntar)
*   Pacotes: marcar **OpenSSH server**

## 3. Primeiro boot - Instalar ferramentas em falta

O minimized não traz `nano`, `netplan` nem `ping`.

```bash
ip a
# anotar IP do enp0s3 (bridge) ex: 192.168.1.68 (se o bridge for com um interface ligado à Eduroam o IP não será atribuído e deverá escolher NAT, repetindo o processo)
# Ligar do host:
ssh itiusr@192.168.1.68

# Instalar o que falta (seguro, não estraga nada)
sudo apt update
sudo apt install netplan.io nano iputils-ping net-tools iproute2 -y --no-install-recommends

# Limpeza (minimized já é limpo, mas é melhor remover restos)
sudo apt purge cloud-init -y
sudo rm -rf /etc/cloud /var/lib/cloud
sudo apt purge snapd -y
sudo apt autoremove -y
```

## 4. Configurar rede do modelo

IMPORTANTE: A rede Host-only foi criada SEM DHCP, por isso `dhcp4: true` no `enp0s8` resulta em interface sem IP.

```bash
sudo nano /etc/netplan/50-vbox.yaml
```

Conteúdo para o modelo (vai ser `node1` = .11):

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    enp0s3:
      dhcp4: true
      optional: true
    enp0s8:
      dhcp4: false
      addresses: [192.168.57.11/24]
      optional: true
```

Aplicar:

```bash
sudo rm -f /etc/netplan/00-installer-config.yaml /etc/netplan/50-cloud-init.yaml
sudo chmod 600 /etc/netplan/*.yaml
sudo netplan generate
sudo netplan apply
ip a
# Deve mostrar enp0s3 com 192.168.1.x (depende do seu sistema) e enp0s8 com 192.168.57.11

ping 192.168.57.10  # ping para o controlador
```

Ajustar hostname do modelo para `node1`:

```bash
sudo hostnamectl set-hostname node1
sudo nano /etc/hosts
# trocar iti-no por node1 na linha 127.0.1.1
sudo reboot
```

Após reboot:

```bash
hostname
ip a  # confirmar 192.168.57.11
df -h # deve mostrar 8.1G / 3.6G 47% - este é o máximo para disco de 10G
```

## 5. Sysprep - Obrigatório antes de clonar

Sem isto os clones ficam com mesmo machine-id, mesmas chaves SSH e colidem.

```bash
sudo apt clean
sudo truncate -s 0 /etc/machine-id
sudo rm -rf /var/lib/dbus/machine-id
sudo ln -s /etc/machine-id /var/lib/dbus/machine-id
sudo rm -f /etc/ssh/ssh_host_*
sudo rm -rf /var/log/*.log /var/log/wtmp /var/log/btmp
history -c
sudo poweroff
```

## 6. Clonagem no VirtualBox

VM desligada `iti-no` (agora `node1`) > Clique direito > Clone:

*   Nome: `node1` (se ainda não renomeou) ou `node2`
*   Tipo: **Full Clone**
*   **Marcar: Generate new MAC addresses** (obrigatório)

Repetir para criar `node2`.

### 6.1 Configurar `node2`

Arrancar `node2` pela consola do VirtualBox (Show):

```bash
# Se o machine-id ainda estiver vazio (ver e alterar:
cat /etc/machine-id
sudo systemd-machine-id-setup

# Recriar chaves SSH (apagadas no sysprep)
sudo ssh-keygen -A
sudo systemctl enable ssh
sudo systemctl restart ssh

# Trocar IP e hostname
sudo nano /etc/netplan/50-vbox.yaml
# trocar 192.168.57.11/24 para 192.168.57.12/24

sudo chmod 600 /etc/netplan/*.yaml
sudo netplan apply

sudo hostnamectl set-hostname node2
sudo nano /etc/hosts  # trocar node1 por node2

sudo reboot
```

### 6.2 Verificar `node1` (se SSH não arrancou)

Se clonou a partir de `iti-no` já com sysprep, o `node1` também ficou sem chaves. Fazer o mesmo que no `node2`:

```bash
sudo systemd-machine-id-setup
sudo ssh-keygen -A
sudo systemctl enable ssh
sudo systemctl restart ssh
```

## 7. Validação a partir do controlador

No controlador (`192.168.57.10`):

```bash
cd ~/ansible-lab
cat > inventory.ini <<'EOF'
[docker_nodes]
node1 ansible_host=192.168.57.11 ansible_user=itiusr
node2 ansible_host=192.168.57.12 ansible_user=itiusr

[docker_nodes:vars]
ansible_become=true
EOF

ansible -i inventory.ini docker_nodes -m ping
# node1 | SUCCESS => pong
# node2 | SUCCESS => pong

ansible -i inventory.ini docker_nodes -a "df -h / | tail -1"
```

Se der `pong` nos dois, o lab está pronto para `ansible-playbook 01-install-docker.yml`.

## Troubleshooting

| Sintoma | Causa | Solução |
|---|---|---|
| `enp0s8` sem IP (`ip a` só mostra `fe80::`) | Rede Host-only sem DHCP + `dhcp4: true` | Usar `dhcp4: false` + `addresses: [192.168.57.X/24]` |
| `WARNING Permissions for /etc/netplan/*.yaml are too open` | Ficheiro 644 | `sudo chmod 600 /etc/netplan/*.yaml` |
| `bash: netplan: command not found` | Minimized não traz | `sudo apt install netplan.io -y` |
| `bash: nano: command not found` | Minimized não traz | `sudo apt install nano -y` |
| `bash: ping: command not found` | Minimized não traz | `sudo apt install iputils-ping -y` |
| SSH não arranca após clone | Chaves apagadas no sysprep | `sudo ssh-keygen -A && sudo systemctl restart ssh` |
| `Failed to start OpenSSH` | `machine-id` vazio | `sudo systemd-machine-id-setup && sudo systemctl restart ssh` |
