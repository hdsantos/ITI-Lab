# ITI - Ansible + Docker + Monitoring Lab
## Laboratório de ITI com Ansible e Docker em VirtualBox

[[Ubuntu 26.04](https://img.shields.io/badge/Ubuntu-26.04%20Resolute-orange)](https://releases.ubuntu.com/)
[[VirtualBox](https://img.shields.io/badge/VirtualBox-7.x-blue)](https://www.virtualbox.org/)
[[Ansible](https://img.shields.io/badge/Ansible-core%202.20-black)](https://docs.ansible.com/)

[🇵🇹 Português](#-português) | [🇬🇧 English](#-english)

---

### 🇵🇹 Português

Base do Laboratório de virtualização para o projeto prático da UC de Infraestruturas e Tecnologias de Informação (ITI), Departamento de Sistemas de Informação, Universidade do Minho. O objetivo é criar um ambiente isolado, reprodutível e seguro para desenvolver competências em Ansible, Docker e Monitorização (Prometheus/Grafana), sem recorrer a cloud pública.

#### Arquitetura

[Arquitetura do Lab](architecture.png)

*   **Host:** Portátil com VirtualBox 7.x
*   **Rede Host-only `192.168.57.0/24` SEM DHCP:** rede de gestão. Isola o lab da rede campus/casa.
*   **Controlador `192.168.57.10`:** 2 vCPU / 4GB RAM / 20GB. Ubuntu Server 26.04.1, incorpora `ansible-core` e `community.docker`. Poderá incluir o Grafana, como opção. É a única VM a que os alunos precisam aceder e devem fazê-lo por SSH a partir do host.
*   **Nós `192.168.57.11`, `.12`...:** 1 vCPU / 2GB RAM / 10GB. Imagem **minimized** do Ubuntu Server 26.04.1. Docker será já instalado via Ansible.
*   **Acesso Internet:** Adapter 1 em NAT (após configuração inicial em Bridge). Apenas para `apt` e pull de imagens.

#### Estrutura do Repositório

```
/ (root)
├── README.md                              <- este ficheiro
├── architecture.png                       <- diagrama acima
├── docs/
│   ├── 01-controlador.md                  <- Setup detalhado do Controlador
│   └── 02-no-referencia-e-clones.md       <- Golden image minimized + clones + sysprep
|   └── 03-pdfer2container.md              <- Colocar o PDFer a correr no node1
│   └── 04-monitorizacao.md                <- Prometheus, cAdvisor e Grafana
│   └── 10-ProjetoSimplificado.md          <- Percurso T-E (individual, NFS + avaliação de métricas)
├── ansible/
│   ├── inventory.ini                      <- Inventário com node1/node2
│   ├── 01-install-docker.yml              <- (a criar) Instala Docker nos nós
│   ├── 02-deploy-monitoring.yml           <- (a criar) Prometheus + Grafana
│   ├── 99-Verify.yml                      <- validação final do laboratório
│   └── group_vars/
│       └── all.yml                        <- opções e perfis da monitorização
├── docker/
│   ├── pdfer-go/
│   │   ├── pdfer                          <- Executável Linux fornecido
│   │   ├── Dockerfile                     <- Imagem do servidor
│   │   ├── compose.yaml                   <- Compose para o Go
│   │   └── store/                         <- Dados persistentes do Go
│   └── pdfer-python/
│   │   ├── pdfer.py                       <- Script Python fornecido
│   │   ├── Dockerfile                     <- Imagem do servidor baseado em Flask
│   │   ├── compose.yaml                   <- Compose para o Python
│   │   └── store/                         <- Dados persistentes do Python
└── scripts/
    └── sysprep.sh                         <- Script de limpeza para clones
```

#### Como começar

**1. Pré-requisitos:** VirtualBox 7.x, ISO Ubuntu Server 26.04.1, 8GB RAM livre no host (mínimo).

**2. Controlador:** Seguir passo-a-passo em [docs/01-controlador.md](docs/01-controlador.md)
> Inclui criação de swap, extensão LVM e instalação correta de `ansible-core` (Nota: não usar `ppa:ansible/ansible`).

**3. Nó de referência:** Seguir [docs/02-no-referencia-e-clones.md](docs/02-no-referencia-e-clones.md)
> Cobre porque o `minimized` não tem `nano`, `netplan`, `ping`, como corrigir `Permissions too open`, e o `sysprep` obrigatório (`ssh-keygen -A` + `systemd-machine-id-setup`) para o SSH voltar a arrancar nos clones.

**4. Instalar Docker nos nós:**
> Cobre a utilização básica de Ansible.
```bash
cd ~/ITI-Lab/ansible
ansible-playbook -i inventory.ini 01-Install-Docker.yml -K
```

**5. Executar o PDFer:** seguir [docs/03-pdfer2container.md](docs/03-pdfer2container.md).
> Cria uma imagem com o executável Linux fornecido (`pdfer`), inicia o servidor num contentor Docker, publica a porta 8080 e mantém a pasta `store` persistente no nó.

Depois do deployment, validar a partir do controlador:

```bash
curl http://192.168.57.11:8080/files
```

**6. Instalar a monitorização:** seguir [docs/04-monitorizacao.md](docs/04-monitorizacao.md).
> Em particular inclui as referências à configuração com e sem Grafana e com apenas 1 nó.
Configuração normal:

```bash
ansible-playbook -i inventory.ini 02-Deploy-Monitoring.yml -K
```

Configuração de memória reduzida, sem Grafana:

```bash
ansible-playbook -i inventory.ini 02-Deploy-Monitoring.yml -K \
  -e monitoring_grafana_enabled=false
```

**7. Validação final:**

```bash
ansible-playbook -i inventory.ini 99-Verify.yml -K
```

**8. Percurso para Trabalhadores-Estudantes (T-E):**
> Se tens estatuto de Trabalhador-Estudante e não podes acompanhar as aulas semanais nem trabalhar em grupo de 6, o laboratório base acima é o mesmo, mas o projeto é diferente. Em vez de 3 fases com iSCSI e cluster multi-nó, farás uma infraestrutura completa mas minimalista num único nó, com storage NFS local em mirror e balanceamento com 2 réplicas, com definição científica obrigatória da carga para métricas. Ver guia dedicado: **[docs/10-ProjetoSimplificado.md](docs/10-ProjetoSimplificado.md)**

#### Notas de Segurança para Alunos

*   OpenSSH com password auth é apenas para lab. Em produção usar chaves.
*   Após configuração inicial, mudar Adapter 1 de Bridge para NAT e aceder apenas via rede Host-only.
*   Nunca expor a rede `192.168.57.0/24` para fora do VirtualBox.

---

### 🇬🇧 English

Hands-on for a base lab to support the project development for Infrastructure and Integration Technologies (ITI) course, Depatment of Information Systems, University of Minho. Goal is to build an isolated, reproducible and secure environment to develope skills in Ansible, Docker and Monitoring (Prometheus/Grafana) without public cloud.

#### Architecture

Same as diagram above.

*   **Host-only `192.168.57.0/24` NO DHCP:** management network, isolated from campus/home.
*   **Controller `192.168.57.10`:** 2 vCPU / 4GB / 20GB. Ubuntu Server 26.04.1 runs `ansible-core` and `community-docker`. It is the only VM that practitioners should access from the host via SSH.
*   **Nodes `192.168.57.11`, `.12`:** 1 vCPU / 2GB / 10GB. Ubuntu Server 26.04.1 minimized. Docker to be installed via Ansible.

#### Repository Structure

Same as PT section. `/docs` contains step-by-step guides, `/ansible` the YAML example playbooks, and `/docker` contains the resources to deply the `pdfer server`.

#### Quick Start

1. Requirements: VirtualBox 7.x, ISO Ubuntu Server 26.04.1, 8GB RAM free in the host (ninimum).
2. Follow [docs/01-controlador.md](docs/01-controlador.md) for controller setup
3. Follow [docs/02-no-referencia-e-clones.md](docs/02-no-referencia-e-clones.md) for golden image and clones
4. Install Docker on nodes:
> Covers Ansible basic utilization
```bash
cd ~/ITI-Lab/ansible
ansible-playbook -i inventory.ini 01-Install-Docker.yml -K
```
5. Follow [docs/03-pdfer2container.md](docs/03-pdfer2container.md) to build and run the PDFer container on `node1`

After deployment verify it form the controller:

```bash
curl http://192.168.57.11:8080/files
```

6. Follow [docs/04-monitorizacao.md](docs/04-monitorizacao.md) to deploy cAdvisor, Prometheus, and optionally Grafana. 
Normal configuration:

```bash
ansible-playbook -i inventory.ini 02-Deploy-Monitoring.yml -K
```

Limited memory resources configuration, without Grafana:

```bash
ansible-playbook -i inventory.ini 02-Deploy-Monitoring.yml -K \
  -e monitoring_grafana_enabled=false
```

7. Run the final validation:

```bash
ansible-playbook -i inventory.ini 99-Verify.yml -K
```

8. **Path for Working Students (T-E):**
> If you have Working Student status and cannot attend weekly classes or work in a group of 6, the base lab above is the same, but the project is different. Instead of 3 phases with iSCSI for distributes storage, and multi-node cluster, you will build a complete but minimal infrastructure on a single computer, with local mirrored NFS storage and 2-replica load balancing, including a mandatory scientific definition of the workload for metrics. See dedicated guide: **[docs/10-ProjetoSimplificado.md](docs/10-ProjetoSimplificado.md)**

#### Key Troubleshooting Learned

| Symptom | Root Cause | Fix |
|---|---|---|
| `enp0s8` has no IPv4 | Host-only without DHCP + `dhcp4: true` | Use `dhcp4: false` + `addresses: [192.168.57.X/24]` |
| `Permissions too open` | netplan file 644 | `chmod 600` |
| `netplan: not found` | minimized has no netplan | `apt install netplan.io` |
| No `ping`/`nano` | minimized is minimal | `apt install iputils-ping nano` |
| SSH fails after clone | sysprep removed host keys | `ssh-keygen -A && systemctl restart ssh` |
| Ansible privilege escalation timeout | Ubuntu is using `sudo-rs` | Select `/usr/bin/sudo.ws` or set `ansible_become_exe` explicitly |
| Prometheus target is `DOWN` | cAdvisor is stopped or the node remains in the inventory while powered off | Check port 8081 and keep only active nodes in `inventory.ini` |
| Docker requires privileges on the controller | `itiusr` is not in the `docker` group | Use `sudo docker ...` |
---

### Autores / Authors

ITI - 2025/2026 - Docente: Henrique Santos
Este laboratório foi desenvolvido com apoio de **Meta AI (Muse Spark)** no diagnóstico de erros, validação de comandos e formatação da documentação.
> This lab was developed with assistance from **Meta AI (Muse Spark)** for troubleshooting, command validation and documentation formatting.
Licença: MIT - Uso educacional.

### Agradecimentos / Acknowledgements

*   Meta AI pela ajuda na depuração da rede Host-only, sysprep e correção dos guias PT/EN.
*   Comunidade Ubuntu e Ansible.
