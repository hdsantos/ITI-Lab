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

> [!IMPORTANT]
> Durante a instalação do OpenSSH nos nós, não importar nesta fase chaves pessoais do GitHub. Manter temporariamente ativa a autenticação por password,
> porque será utilizada pelo `ssh-copy-id` para instalar a chave pública do controlador.
>
> Depois de confirmar o acesso do controlador por chave pública, a autenticação SSH por password poderá ser desativada.

## 3. Primeiro boot - Instalar ferramentas em falta

O minimized não traz `nano`, `netplan` nem `ping`. Nota: o `python3-flask` foi adicionado porque pode ser desejável fazer o pdfer em python.

```bash
ip a
# anotar IP do enp0s3 (bridge) ex: 192.168.1.68 (se o bridge for com um interface ligado à Eduroam o IP não será atribuído e deverá escolher NAT, repetindo o processo)
# Ligar do host (usar o username criado na instalação):
ssh <user>@192.168.1.68

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

> [!IMPORTANT]
> Depois de executar o `sysprep` e desligar a VM `iti-no`, **não volte a arrancá-la, pelo menos antes de concluir todas as clonagens**.
>
> Se esta VM for iniciada, o sistema poderá regenerar o `machine-id` e as chaves SSH. Os clones criados posteriormente poderão então herdar os mesmos identificadores, provocando conflitos.

## 6. Clonagem no VirtualBox

Com a VM `iti-no` desligada, no VirtaulBox Manager e com o rato sobre a VM `iti-no` > Clique direito > Clone:

*   Nome: `node1` ou `node2`, consoante o caso
*   Tipo: **Full Clone**
*   **Marcar: Generate new MAC addresses** (obrigatório)

Repetir para criar qualquer outro nó adicional.

### 6.1 Inicializar cada nó após a clonagem

Os passos seguintes são obrigatórios no `node1` e no `node2`, porque ambos
foram criados a partir da imagem depois da remoção do `machine-id` e das
chaves SSH.

Arrancar cada VM pela consola do VirtualBox e executar:

```bash
sudo systemd-machine-id-setup
sudo ssh-keygen -A
sudo systemctl enable ssh
sudo systemctl restart ssh
```
Em cada caso confirmar a alteração e o estado do serviço SSH:

```bash
cat /etc/machine-id
ls -l /etc/ssh/ssh_host_*_key.pub
systemctl status ssh --no-pager
```

O `machine-id` e as chaves SSH devem ser diferentes em cada nó.

### 6.2 Configurar `node2`

Arrancar `node2` pela consola do VirtualBox (Show):

```bash
# Ajustar o IP e hostname
sudo nano /etc/netplan/50-vbox.yaml
# trocar 192.168.57.11/24 para 192.168.57.12/24

sudo chmod 600 /etc/netplan/*.yaml
sudo netplan apply

sudo hostnamectl set-hostname node2
sudo nano /etc/hosts  # trocar node1 por node2

sudo reboot
```
Esta última operação terá que ser feita para todos os nós criados, exceto o `node1` porque ele herdou o IP e o `hostname` corretos do nó de referência que serve de base a todos os clones.

## 7. Validação a partir do controlador

No controlador (`192.168.57.10`):

Nesta fase e antes de validar a operação do Ansible, é necessário copiar a chave pública do controlador, criada durante a sua instalação. Relembra-se aqui que o Ansible não usa a autenticação por password no SSH, uma vez que não é suposto executar interativamente. Assim, recorre habitualmente à autenticação por chave pública/privada. **Nota: não se esqueça de ajustar o username para o seu caso**

```bash
ssh-copy-id itiusr@192.168.57.11
# Se estiverem os dois nós em execuçã
ssh-copy-id itiusr@192.168.57.12
```
e agora a verificação (NOTA: Caso o controlador tenha sido criado anteriormente e o repositório ITI-Lab tenha entretanto sido atualizado, execute `git pull` em `~/ITI-Lab` antes de continuar.

```bash
cd ~/ITI-Lab/ansible
cat > inventory.ini <<'EOF'
[docker_nodes]
node1 ansible_host=192.168.57.11 ansible_user=itiusr
node2 ansible_host=192.168.57.12 ansible_user=itiusr

[docker_nodes:vars]
ansible_python_interpreter=/usr/bin/python3
ansible_become_exe=/usr/bin/sudo.ws
EOF
```

NOTA: este ficherio de inventário inclui os dois nós. Se por alguma razão apenas tiver um nó, ou se tiver mais do que dois, deve apenas atualizar este ficheiro de inventário.

```bash
ansible -i inventory.ini docker_nodes -m ping
# node1 | SUCCESS => pong
# node2 | SUCCESS => pong

ansible -i inventory.ini docker_nodes -a "df -h"
```

Se der `pong` nos nós indicados, o lab está pronto para a fase seguinte que consiste na instalção do Docker. O último comando ilustra como é possível executar remotamente uma operação nos nós usando o ansible (ambos executarão o comando `df -h` usando o interpretador do python.

## 8. Instalação do Docker nos nós

Depois de confirmar que os nós respondem ao módulo `ping`, instalar o Docker através do playbook fornecido, a partir do **controlador** (o respetivo playbook é executado no controlador e instala Docker remotamente em todos os hosts definidos no grupo `docker_nodes` do ficheiro `inventory.ini`).

```bash
# assumindo que está na diretoria ~/ITI-Lab/ansible
ansible-playbook -i inventory.ini 01-Install-Docker.yml -K -e ansible_become_exe=/usr/bin/sudo.ws
```
***Nota: o K maísculo no último comando***

A opção `-K` solicita a password de `sudo` do utilizador `itiusr`, necessária porque a instalação de pacotes e a configuração do serviço Docker exigem privilégios administrativos. Como se pode observar, o `playbook` adiciona o utilizador `itiusr` ao grupo `docker` para que não seja necessário executar os comandos Docker com sudo. No entanto, essa alteração exige a reinicialização dos nós antes de entrar em efeito. Em cada um dos nós, executar:

```bash
sudo reboot
```

NOTA: Se durante o ping obtiver um **warning** relativo ao python, isso não é um problema. A secção [docker_nodes:vars] tem uma declaração que deve evitar esse aviso, mas esse detalhe pode sofrer alterações com versões diferentes.

NOTA: a versão anterior desta documentação incluia a declaração **ansible_become=true**, que indicava ao Ansible para executar os comandos como root. Essa opção levanta algumas dificuldades de configuração nos nós e foi abandonada.

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
