# Lab Ansible + Docker + Monitoring — Parte 4: Monitorização com Prometheus, cAdvisor e Grafana

Este guia descreve como instalar a infraestrutura de monitorização do laboratório através de Ansible.

A solução utiliza:

- **cAdvisor** em cada nó Docker, para recolher métricas dos contentores;
- **Prometheus** no controlador, para recolher e armazenar as séries temporais;
- **Grafana**, opcionalmente, no controlador, para construir dashboards.

O Grafana pode ser desativado em computadores com menos memória. O Prometheus continua a recolher e a permitir consultar ou exportar as métricas.

## 1. Arquitetura

```text
Host
└── Controlador — 192.168.57.10
    ├── Ansible
    ├── Prometheus — porta 9090
    └── Grafana — porta 3000 (opcional)

    ├── node1 — 192.168.57.11
    │   ├── PDFer — porta 8080
    │   └── cAdvisor — porta 8081
    │
    └── node2 — 192.168.57.12 (opcional)
        └── cAdvisor — porta 8081
```

O cAdvisor mede CPU, memória, rede e armazenamento **por contentor**. Não mede diretamente operações internas do PDFer, como o número de pedidos, a latência de cada endpoint ou o tempo gasto na cifra. Essas métricas exigem testes externos ou instrumentação específica da aplicação.

## 2. Pré-requisitos

Antes de iniciar esta etapa, confirmar que:

- o controlador e os nós estão ligados;
- o repositório `ITI-Lab` está atualizado no controlador;
- o Ansible consegue contactar todos os nós presentes no inventário;
- o Docker está instalado nos nós através de `01-Install-Docker.yml`;
- o PDFer está em execução no `node1`;
- o controlador e os nós estão configurados para usar `sudo.ws`, ou os playbooks indicam explicitamente `ansible_become_exe: /usr/bin/sudo.ws`.

No controlador (se ainda não foi feito):

```bash
cd ~/ITI-Lab
git pull

cd ansible
ansible -i inventory.ini docker_nodes -m ping
```

## 3. Configuração com um ou dois nós

O inventário deve conter apenas as máquinas que estão efetivamente disponíveis.

### 3.1 Dois nós

```ini
[docker_nodes]
node1 ansible_host=192.168.57.11 ansible_user=itiusr
node2 ansible_host=192.168.57.12 ansible_user=itiusr

[docker_nodes:vars]
ansible_python_interpreter=/usr/bin/python3
```

### 3.2 Apenas um nó

Em computadores com recursos limitados, comentar ou remover o `node2`:

```ini
[docker_nodes]
node1 ansible_host=192.168.57.11 ansible_user=itiusr
# node2 ansible_host=192.168.57.12 ansible_user=itiusr

[docker_nodes:vars]
ansible_python_interpreter=/usr/bin/python3
```

Não se deve manter no inventário um nó que esteja desligado: o Ansible tentará contactá-lo e o Prometheus ficará configurado com um alvo indisponível.

## 4. Variáveis da monitorização

As opções encontram-se em `ansible/group_vars/all.yml`. Já está configurado, mas pode verificar e sobretudo ajustar, caso tenha introduzido alterações à arquitetura:

```yaml
# Endereço do controlador acessível a partir do host
monitoring_controller_address: 192.168.57.10

# cAdvisor
monitoring_cadvisor_enabled: true
monitoring_cadvisor_image: ghcr.io/google/cadvisor:0.60.6
monitoring_cadvisor_port: 8081
monitoring_cadvisor_memory: 128m

# Prometheus
monitoring_prometheus_port: 9090
monitoring_prometheus_scrape_interval: 10s
monitoring_prometheus_retention_time: 3d
monitoring_prometheus_retention_size: 1GB
monitoring_prometheus_memory: 512m

# Grafana
monitoring_grafana_enabled: true
monitoring_grafana_port: 3000
monitoring_grafana_memory: 256m

# Nós onde se espera encontrar o PDFer
pdfer_nodes:
  - node1
```

Os limites de retenção impedem que os dados do Prometheus cresçam indefinidamente e ocupem todo o disco do controlador.

## 5. Perfis de recursos

### 5.1 Configuração normal

Para um computador com recursos suficientes:

- controlador com Prometheus e Grafana;
- `node1` e `node2` com cAdvisor;
- `monitoring_grafana_enabled: true`.

### 5.2 Configuração reduzida

Para um computador com 8 GB de RAM:

- controlador com aproximadamente 3 GB;
- apenas o `node1` ligado;
- Prometheus ativo;
- Grafana desativado.

Pode alterar `all.yml`:

```yaml
monitoring_grafana_enabled: false
```

Ou desativar o Grafana apenas durante a execução:

```bash
ansible-playbook -i inventory.ini 02-Deploy-Monitoring.yml -K \
  -e monitoring_grafana_enabled=false
```

A opção fornecida com `-e` tem precedência sobre o valor de `all.yml`.

## 6. Validar e executar o playbook

No controlador:

```bash
cd ~/ITI-Lab/ansible
```

Validar primeiro a sintaxe:

```bash
ansible-playbook -i inventory.ini 02-Deploy-Monitoring.yml --syntax-check
```

Executar a configuração normal:

```bash
ansible-playbook -i inventory.ini 02-Deploy-Monitoring.yml -K
```

O parâmetro `-K` solicita a password de elevação de privilégios. O playbook:

1. cria e inicia um cAdvisor em cada nó listado em `docker_nodes`;
2. instala Docker e Docker Compose no controlador, caso sejam necessários;
3. cria a configuração do Prometheus a partir do inventário;
4. inicia Prometheus e, quando ativado, Grafana;
5. configura automaticamente o Prometheus como fonte de dados do Grafana;
6. verifica se o cAdvisor e o Prometheus respondem.

No controlador, o utilizador `itiusr` não pertence necessariamente ao grupo `docker`. Os comandos Docker executados manualmente devem, por isso, usar `sudo`:

```bash
sudo docker ps
sudo docker compose ls
```

## 7. Aceder aos serviços

| Serviço | Endereço |
|---|---|
| PDFer | `http://192.168.57.11:8080` |
| cAdvisor do `node1` | `http://192.168.57.11:8081` |
| cAdvisor do `node2` | `http://192.168.57.12:8081` |
| Prometheus | `http://192.168.57.10:9090` |
| Grafana | `http://192.168.57.10:3000` |

O Grafana só estará disponível quando `monitoring_grafana_enabled` estiver ativo. As credenciais iniciais do laboratório são:

```text
utilizador: admin
password: admin123
```

Estas credenciais destinam-se apenas à rede isolada do laboratório.

## 8. Confirmar os targets do Prometheus

Abrir:

```text
http://192.168.57.10:9090/targets
```

Todos os targets deverão apresentar o estado `UP`:

- o próprio Prometheus;
- o cAdvisor do `node1`;
- o cAdvisor do `node2`, quando estiver definido no inventário.

Numa configuração com dois nós, são esperados três targets. Com apenas um nó, são esperados dois.

## 9. Consultas PromQL iniciais

As consultas podem ser executadas diretamente na interface do Prometheus, em `http://192.168.57.10:9090`.

### 9.1 CPU por contentor

```promql
sum by (name) (rate(container_cpu_usage_seconds_total{name!=""}[1m]))
```

### 9.2 Memória utilizada

```promql
container_memory_working_set_bytes{name!=""}
```

### 9.3 Tráfego de rede recebido

```promql
rate(container_network_receive_bytes_total{name!=""}[1m])
```

### 9.4 Tráfego de rede transmitido

```promql
rate(container_network_transmit_bytes_total{name!=""}[1m])
```

Os nomes e labels disponíveis podem ser consultados no endpoint `/metrics` de cada cAdvisor.

## 10. Utilizar Prometheus sem Grafana

O Grafana é apenas a camada de visualização. Quando estiver desativado, o Prometheus continua a recolher e armazenar as métricas.

É possível:

- executar consultas na interface Web do Prometheus;
- utilizar a API HTTP do Prometheus;
- importar os resultados JSON no Excel através do Power Query;
- tratar os dados com Python, R ou outra ferramenta de análise temporal.

O endpoint para consultas temporais é:

```text
http://192.168.57.10:9090/api/v1/query_range
```

Exemplo:

```bash
curl -G 'http://localhost:9090/api/v1/query_range' \
  --data-urlencode 'query=container_memory_working_set_bytes{name!=""}' \
  --data-urlencode 'start=2026-10-11T14:00:00Z' \
  --data-urlencode 'end=2026-10-11T15:00:00Z' \
  --data-urlencode 'step=10s'
```

As datas do exemplo devem ser substituídas pelo intervalo que se pretende analisar.

## 11. Validação final do laboratório

Depois de instalar o PDFer e a infraestrutura de monitorização, executar:

```bash
ansible-playbook -i inventory.ini 99-Verify.yml -K
```

O playbook valida, sem modificar a infraestrutura:

- espaço em disco e memória dos nós;
- Docker;
- cAdvisor;
- PDFer nos nós indicados em `pdfer_nodes`;
- Prometheus e respetivos targets;
- Grafana, quando estiver ativado.

Uma execução correta deverá terminar sem tarefas `failed` ou `unreachable`.

## 12. Troubleshooting

| Sintoma | Causa provável | Solução |
|---|---|---|
| `Timeout waiting for privilege escalation prompt` | O Ansible está a usar `sudo-rs` | Selecionar `/usr/bin/sudo.ws` ou definir `ansible_become_exe: /usr/bin/sudo.ws` |
| `image ... not found` ao iniciar cAdvisor | Tag incorreta ou desatualizada | Confirmar `monitoring_cadvisor_image: ghcr.io/google/cadvisor:0.60.6` |
| Um nó aparece como `UNREACHABLE` | O nó está desligado mas permanece no inventário | Ligar o nó ou comentar a respetiva linha em `inventory.ini` |
| Target do Prometheus aparece `DOWN` | cAdvisor parado, endereço incorreto ou problema de rede | Testar `curl http://IP_DO_NO:8081/metrics` a partir do controlador |
| Prometheus responde, mas Grafana não | Grafana desativado ou ainda a iniciar | Confirmar `monitoring_grafana_enabled` e executar `sudo docker ps` no controlador |
| `permission denied` ao executar Docker no controlador | `itiusr` não pertence ao grupo `docker` | Usar `sudo docker ...`; o playbook já utiliza elevação de privilégios |
| Porta 8081 ocupada | Outro serviço utiliza a porta do cAdvisor | Executar `sudo ss -ltnp | grep :8081` no nó |
| O disco do controlador fica cheio | Retenção excessiva do Prometheus | Reduzir `monitoring_prometheus_retention_time` ou `monitoring_prometheus_retention_size` |

