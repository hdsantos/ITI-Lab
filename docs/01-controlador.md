# Lab Ansible + Docker + Monitoring - Setup do Controlador (VirtualBox)

Guia para Ubuntu Server 26.04 (Resolute) com VirtualBox 7.x. Testado com controlador de 4GB RAM.

Nas instruções que se seguem é assumido que os alunos estão familiarizados com as operações básicas no ambiente de virtualização (criar VMs; tipos de redes - bridge, host-only e NAT; configuração básica das VMs, etc.)

## 1. Rede VirtualBox

No VirtualBox > Tools > Network > **Host-only Networks** > Create.

Crie uma rede **SEM DHCP**, por exemplo:

*   **IPv4:** `192.168.57.1/24`
*   Máscara: `255.255.255.0`
*   DHCP: Desligado

Esta rede será a rede de gestão Ansible: `192.168.57.10` controlador, `192.168.57.11`, `.12`... nós.

## 2. Criação da VM Controlador

*   ISO: Ubuntu Server 26.04.1
*   **Desmarcar `Unattended Installation` / Skip Unattended Install** - Se não desmarcarem, o cloud-init fica agarrado e a rede não funciona como queremos.
*   Recursos: **2 vCPU, 4096 MB RAM mínimo, 20 GB disco**
*   Rede:
    *   Adapter 1: **Bridged** (durante a instalação, para ter internet e fazer SSH do host)
    *   Adapter 2: **Host-only**, escolher a rede `192.168.57.1/24` criada

### 2.1 Configuração de Processador

VM desligada > Settings > System:

*   Motherboard > Enable I/O APIC: **ON**
*   Processor > **Enable PAE/NX: ON** (NX é obrigatório para 64-bit)
*   Processor > Enable Nested Paging: **ON**
*   Processor > Enable Nested VT-x/AMD-V: **OFF** (só é preciso para VM-dentro-de-VM/KVM. Para Docker deixa OFF, é mais rápido)
*   Acceleration > Paravirtualization Interface: **KVM** (melhor para Linux)

> **NOTA Segurança:** Durante a configuração inicial é preferível o Adapter 1 em Bridge para aceder por SSH do host Linux. Após a configuração, por segurança, devem mudar o Adapter 1 para **NAT** e passar a aceder ao controlador apenas via rede Host-only `192.168.57.10`.

## 3. Instalação do Ubuntu

Instalação manual normal (~3 min). Quando perguntar pacotes, selecionar **OpenSSH server**.

> O OpenSSH por defeito permite password auth, o que é considerado vulnerável em produção, mas para lab é útil para o primeiro acesso.

No primeiro boot:

```bash
ip a  # anotar IP do enp0s3 (Bridge)

# A partir do HOST Linux:
ssh <user>@<ip-do-enp0s3>
# yes ao fingerprint
```

## 4. Limpeza do cloud-init

O Ubuntu Server traz cloud-init por defeito. Para um controlador Ansible é lixo e atrasa o boot em 2 min.

Remover completamente (recomendado):

```bash
sudo apt purge cloud-init -y
sudo rm -rf /etc/cloud /var/lib/cloud
sudo apt autoremove -y
sudo reboot
```

Alternativa (não recomendada, só desativa):

```bash
sudo touch /etc/cloud/cloud-init.disabled
sudo systemctl disable cloud-init cloud-config cloud-final
```

## 5. Configuração de Rede Definitiva

Sem isto, o boot fica 2 min à espera de gateway no segundo interface.

```bash
sudo nano /etc/netplan/50-vbox.yaml
```

Colar (atenção à indentação YAML - 2 espaços):

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    enp0s3:  # Placa 1 - NAT ou Bridge - Internet
      dhcp4: true
      optional: true
    enp0s8:  # Placa 2 - Host-Only - 192.168.57.0/24
      dhcp4: false
      addresses:
        - 192.168.57.10/24
      optional: true
```

Aplicar:

```bash
sudo rm -f /etc/netplan/00-installer-config.yaml /etc/netplan/50-cloud-init.yaml
sudo netplan apply
ip a  # deve mostrar enp0s8 com 192.168.57.10
```

A partir de agora acedam por `ssh <user>@192.168.57.10`.

## 6. Swap e Extensão do Disco

O Ubuntu cria o LV com ~50% do disco e sem swap. O `ansible` precisa de memória.

```bash
# Verificar
df -h
free -h
# Se / tiver 9.8G em vez de 18-19G, ou Swap 0B, executar:

sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Esticar LVM para usar disco todo
sudo lvextend -l +100%FREE /dev/mapper/ubuntu--vg-ubuntu--lv
sudo resize2fs /dev/mapper/ubuntu--vg-ubuntu--lv

df -h  # deve ficar com ~18G e 41% usado
```

## 7. Base Ansible

**IMPORTANTE:** Não usem o PPA `ppa:ansible/ansible`. O pacote `ansible` completo tem 400MB+ e congela em VMs com pouca RAM. Usem `ansible-core`.

```bash
# Se tiverem adicionado o PPA antes, remover:
sudo rm -f /etc/apt/sources.list.d/ansible-*.list
sudo apt update

sudo apt install software-properties-common git openssh-client -y --no-install-recommends
sudo apt install ansible-core python3-pip -y --no-install-recommends

ansible --version  # deve mostrar ansible [core 2.20.x]

ansible-galaxy collection install community.docker
```

Se o `apt` ficar preso nos 13%/20% no unpacking:
```bash
sudo pkill -9 dpkg; sudo rm -f /var/lib/dpkg/lock*
sudo dpkg --configure -a
sudo apt install -f -y
```

## 8. Guest Additions (Opcional)

Necessário para clipboard e pastas partilhadas.

```bash
sudo apt install build-essential dkms linux-headers-$(uname -r) -y
# No menu do VirtualBox: Devices > Insert Guest Additions CD
sudo mkdir -p /mnt/cdrom
sudo mount /dev/cdrom /mnt/cdrom
sudo /mnt/cdrom/VBoxLinuxAdditions.run
sudo reboot
```

## 9. Snapshot

Neste ponto, com rede, swap e ansible-core a funcionar, façam um snapshot: `Controlador-Pronto`.

Próximo passo: clonar nós minimized (sem Docker) e instalar Docker via Ansible.
