# 10 - Projeto Simplificado para Trabalhadores-Estudantes (T-E)

> **Este guia complementa o README.md principal.** Destina-se a alunos com estatuto de Trabalhador-Estudante que realizam o projeto individualmente ou em grupos de 2, sem acompanhamento semanal. Mantém os 3 pilares do projeto regular (métricas, armazenamento, processamento) mas numa arquitetura minimalista de 1 só computador.

### Contexto

Os alunos regulares trabalham em grupos de 6, com 2h/semana de aula + 4h autónomo (5 ECTS), estando o projeto dividido em 3 fases. Os alunos T-E não têm essa disponibilidade nem um ambiente de trabalho colaborativo idêntico. Este projeto é **uma fase única integradora**, com carga estimada de 50-60h totais.

Arquitetura base continua a ser a do [ITI-Lab](https://github.com/hdsantos/ITI-Lab): VM Controlador `192.168.57.10` com Ansible/Prometheus/Grafana + 1 Nó `192.168.57.11` com Docker. Ver `docs/01-controlador.md` e `docs/02-no-referencia-e-clones.md`.

O servidor é o **pdfer** (`docker/pdfer-go` ou `docker/pdfer-python`).

---

### Arquitetura Alvo T-E (1 Nó)

```
[Host] -> [Controlador 57.10] --Ansible--> [Nó 57.11 - Docker]
                                            ├── pdfer-1 (container :8080)
                                            ├── pdfer-2 (container :8081) - réplica
                                            ├── nginx-proxy (container :80 -> pdfer-1/2)
                                            └── /mnt/pdfer-data -> NFS mount do TrueNAS
[TrueNAS VM 57.20 - 1 vCPU/2GB/2x10GB discos virtuais em MIRROR]
```

**Diferença chave para o projeto de alunos regulares:** Não se pede discos distribuídos. O aluno T-E cria 2 discos virtuais locais de 10GB no VirtualBox e anexa à VM TrueNAS. Assim garante tolerância a falhas sem dependência de grupo. Usa-se **NFS** em vez de iSCSI - mais simples, stateless, sem necessidade de coordenação de LUNs.

---

### Desafio 1 - Deploy e Monitorização (40%)

**Objetivo:** Equivalente à Fase 1 regular.

1.  Usar Ansible do Controlador para instalar Docker no Nó (`ansible/01-install-docker.yml`).
2.  Deploy do pdfer via `docker compose` (ver `docs/03-pdfer2container.md`).
3.  **Monitorização obrigatória** (ver `docs/04-monitorizacao.md`):
    *   Dashboard Grafana com: CPU/Mem Nó (Node Exporter), CPU/Mem containers (cAdvisor), estado dos targets Prometheus.
    *   Criar 1 alerta: `pdfer down` ou `CPU > 80% por 2m`.

**Entregável D1:** `docker-compose.yml` ajustado, print do `http://192.168.57.10:3000` (Grafana) e do `http://192.168.57.10:9090/targets`.

### Desafio 2 - NAS com Tolerância a Falhas - NFS (30%)

**Objetivo:** Equivalente à Fase 2 regular, mas sem iSCSI e só com discos locais

**Porquê NFS e não iSCSI para T-E:** iSCSI implica gestão de initiator/target e LUNs partilhados, que só faz sentido com múltiplos nós a competir pelo mesmo storage. Para um aluno isolado, NFS é mais realista, mais simples de depurar e igualmente válido como NAS com tolerância a falhas.

**Passos:**

1.  Criar uma VM TrueNAS Core (ou XigmaNAS) `192.168.57.20` com 2 discos virtuais de 2GB (VirtualBox > VM > Settings > Storage > Add Hard Disk), para além do disco de sistema.
2.  No TrueNAS:
    *   Storage > Pools > Create Pool > 2 discos em **Mirror** (equivale ao conceito de RAIDZ-1 pedido aos regulares, mas exequível a solo - 1 falha tolerada). Formatar como ZFS.
    *   Datasets > `pdfer-share` > Share Type: NFS
    *   Sharing > NFS Shares > Add, Path `/mnt/pool0/pdfer-share`, Maproot User `root`, Networks `192.168.57.0/24`
3.  No Nó `57.11`:

```bash
   # Ajustar conforme o caso
   sudo apt install nfs-common
   sudo mkdir -p /mnt/pdfer-data
   sudo mount -t nfs 192.168.57.20:/mnt/pool0/pdfer-share /mnt/pdfer-data
   # Persistir em /etc/fstab
```
4.  Alterar o ficheiro `compose.yaml` para usar volume bind `/mnt/pdfer-data:/app/store`
5.  **Teste de fiabilidade:** No TrueNAS, Storage > Disks > Offline um disco. Correr `zpool status` e mostrar DEGRADED mas ONLINE. Fazer upload no pdfer e provar que continua a funcionar. Depois Online + Resilver.

**Entregável D2:** Prints de `zpool status` saudável, DEGRADED e após resilver + print do mount NFS no nó + gráfico Grafana de I/O durante a falha.

### Desafio 3 - Escalabilidade e Failover com Reverse Proxy (30%)

**Objetivo:** Equivalente à Fase 3 regular.

1.  No Nó, correr 2 réplicas do pdfer:
```yaml
   # compose.override para T-E
   # Ajustar conforme necessário
   services:
     pdfer-1: ... ports 8080
     pdfer-2: ... ports 8081
     nginx-proxy:
       image: nginx:alpine
       ports: ["80:80"]
       volumes: ["./nginx.conf:/etc/nginx/nginx.conf:ro"]
```
2.  Configurar através de `nginx.conf`:
```
   upstream pdfer_cluster {
       server pdfer-1:8080 max_fails=2 fail_timeout=10s;
       server pdfer-2:8080 max_fails=2 fail_timeout=10s;
   }
   server { location / { proxy_pass http://pdfer_cluster; } }
```
3.  **Teste de failover:** `docker stop pdfer-1` e provar via `curl http://192.168.57.11/files` que o serviço continua via pdfer-2. Mostrar no Prometheus que o target pdfer-1 fica down mas o serviço global up.

**Entregável D3:** `nginx.conf`, logs `access.log` mostrando round-robin, e prova de failover.

---

### Definição Científica da Carga para Métricas (OBRIGATÓRIO para T-E)

Para que as métricas sejam comparáveis, não basta dizer "testei com muitos ficheiros". Têm de definir a carga de forma reprodutível. É este o ponto que será mais avaliado.

**Devem definir no relatório:**

1.  **Ferramenta:** Usar uma e só uma para todos os testes: `k6`, `wrk` ou `ApacheBench (ab)`. Recomendado: `k6` (tem script JS reprodutível).
2.  **Perfis de carga (3 perfis obrigatórios):**

| Perfil | Descrição | Ficheiros | Tamanho | Concorrência | Pedidos totais |
| :--- | :--- | :--- | :--- | :--- | :--- |
| S | Small objects | 100 ficheiros | 1-10 KB | 1, 10, 50 | 1000 |
| M | Medium objects | 20 ficheiros | 1 MB | 1, 10, 50 | 200 |
| L | Large objects | 5 ficheiros | 10 MB | 1, 10 | 50 |

3.  **Exemplo de script k6 reprodutível (a incluir no repo):**
    ```javascript
    // k6-load.js
    import http from 'k6/http';
    export let options = { vus: 10, duration: '30s' };
    export default function() {
      http.get('http://192.168.57.11/files');
      http.post('http://192.168.57.11/files', { file: http.file(open('./1MB.bin','b'), '1MB.bin') });
    }
    ```

4.  **Métricas a reportar para cada perfil e cada cenário (Local vs NFS vs NFS Degraded vs Cluster):**
    *   Latência: p50, p95, p99 (ms) - do k6
    *   Throughput: req/s e MB/s
    *   Erros: % de falhas
    *   Sistema: CPU% e Mem do Nó e do TrueNAS (Grafana), IOPS e latência ZFS (`zpool iostat 1`)

5.  **Cenários de comparação obrigatórios:**
    *   A) pdfer com disco local (baseline)
    *   B) pdfer com NFS Mirror saudável
    *   C) pdfer com NFS Mirror DEGRADED (1 disco offline)
    *   D) pdfer via Nginx com 1 réplica down

Apresentar em tabela no relatório. Ex: "Carga M, VUs=10: Latência p95 A=120ms, B=180ms (+50%), C=210ms (+75%), D=130ms".

Isto permite discutir cientificamente a penalização do armazenamento em rede e o ganho de tolerância.

---

### Entrega

*   Repositório Git (fork do ITI-Lab) com pasta `/docs/10-ProjetoSimplificado/` contendo este guia + `k6-load.js` + `nginx.conf` + `compose.yaml` final
*   Relatório Markdown/PDF (6-8 páginas) com arquitetura, definição de carga, tabelas de métricas e testes de falha
*   Discussão oral de 15 min (Zoom/presencial)

### Avaliação

*   D1 40% + D2 30% + D3 30% + Bónus 10% documentação reprodutível
*   Critério de reprovação: não definir carga de forma científica ou não fazer teste de falha documentado.

---
*ITI 2025/2026 - Docente Henrique Santos - Percurso T-E*
