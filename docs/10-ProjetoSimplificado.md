# 10 - Projeto Simplificado para Trabalhadores-Estudantes (T-E) / Simplified Project for Working Students (T-E)

[🇵🇹 Português](#-português) | [🇬🇧 English](#-english)

### 🇵🇹 Português

> **Este guia complementa o README.md principal.** Destina-se a alunos com estatuto de Trabalhador-Estudante que realizam o projeto individualmente ou em grupo de 2, sem acompanhamento semanal. Mantém os 3 pilares do projeto regular (computação, armazenamento, processamento) mas numa arquitetura minimalista de 1 só computador.

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

**Diferença chave para o projeto de alunos regulares:** Não se pede disco a cada colega. O aluno T-E cria 2 discos virtuais locais de 2GB no VirtualBox e anexa à VM TrueNAS. Assim garante tolerância a falhas sem dependência de grupo. Usa-se **NFS** em vez de iSCSI - mais simples, stateless, sem necessidade de coordenação de LUNs.

---

### Desafio 1 - Deploy e Monitorização (40%)

**Objetivo:** Equivalente à Fase 1 regular.

1.  Usar Ansible do Controlador para instalar Docker no Nó (`ansible/01-install-docker.yml`).
2.  Deploy do pdfer via `docker compose` (ver `docs/03-pdfer2container.md`).
3.  **Monitorização obrigatória** (ver `docs/04-monitorizacao.md`):
    *   Dashboard Grafana com: CPU/Mem Nó (Node Exporter), CPU/Mem containers (cAdvisor), estado dos targets Prometheus.
    *   Criar 1 alerta: `pdfer down` ou `CPU > 80% por 2m`.

**Entregável D1:** `docker-compose.yml`, print do `http://192.168.57.10:3000` (Grafana) e do `http://192.168.57.10:9090/targets`.

### Desafio 2 - NAS com Tolerância a Falhas - NFS (30%)

**Objetivo:** Equivalente à Fase 2 regular, mas sem iSCSI e só com discos locais.

**Porquê NFS e não iSCSI para T-E:** iSCSI implica gestão de initiator/target e LUNs partilhados, que só faz sentido com múltiplos nós a competir pelo mesmo storage. Para um aluno isolado, NFS é mais realista, mais simples de depurar e igualmente válido como NAS com tolerância a falhas.

**Passos:**

1.  Criar VM TrueNAS Core (ou XigmaNAS) `192.168.57.20` com 2 discos virtuais de 2GB (VirtualBox > VM > Settings > Storage > Add Hard Disk), para além do disco de sistema.
2.  No TrueNAS:
    *   Storage > Pools > Create Pool > 2 discos em **Mirror** (equivale ao conceito de RAIDZ-1 pedido aos regulares, mas exequível a solo - 1 falha tolerada). Formatar como ZFS.
    *   Datasets > `pdfer-share` > Share Type: NFS
    *   Sharing > NFS Shares > Add, Path `/mnt/pool0/pdfer-share`, Maproot User `root`, Networks `192.168.57.0/24`
3.  No Nó `57.11`:
```bash
   sudo apt install nfs-common
   sudo mkdir -p /mnt/pdfer-data
   sudo mount -t nfs 192.168.57.20:/mnt/pool0/pdfer-share /mnt/pdfer-data
   # Persistir em /etc/fstab
```
4.  Alterar ficheiro `compose.yaml` para usar volume bind `/mnt/pdfer-data:/app/store`
5.  **Teste de fiabilidade:** No TrueNAS, Storage > Disks > Offline um disco. Correr `zpool status` e mostrar DEGRADED mas ONLINE. Fazer upload no pdfer e provar que continua a funcionar. Depois Online + Resilver.

**Entregável D2:** Prints de `zpool status` saudável, DEGRADED e após resilver + print do mount NFS no nó + gráfico Grafana de I/O durante a falha.

### Desafio 3 - Escalabilidade e Failover com Reverse Proxy (30%)

**Objetivo:** Equivalente à Fase 3 regular.

1.  No Nó, correr 2 réplicas do pdfer:
```yaml
   # compose.override para T-E
   services:
     pdfer-1: ... ports 8080
     pdfer-2: ... ports 8081
     nginx-proxy:
       image: nginx:alpine
       ports: ["80:80"]
       volumes: ["./nginx.conf:/etc/nginx/nginx.conf:ro"]
```
2.  `nginx.conf` com:
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

Para que as métricas sejam comparáveis, não basta dizer "testei com muitos ficheiros". Têm de definir a carga de forma reprodutível. É este o ponto que será mais avaliado nos T-E.

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

*   Repositório Git (fork do ITI-Lab) com pasta `/docs/10-ProjetoSimplificado/` contendo este guia + `k6-load.js` + `nginx.conf` + `compose.yaml` final (ou cópia dos ficheiros por email)
*   Relatório Markdown/PDF (6-8 páginas) com arquitetura, definição de carga, tabelas de métricas e testes de falha
*   Discussão oral de 15 min (Zoom/presencial)


### Leituras Recomendadas (definição de carga e percentis)

Para definirem cientificamente a carga e interpretarem as métricas, recomendam-se estas duas referências:

**1. Percentis p50/p95/p99 - porque a média mente:**
- One2N - "Percentiles in SRE: Why averages lie about latency" - define p50 como mediana (típico), p95 como alerta precoce (5% mais lento) e p99 como cauda crítica (1% mais lento), e mostra porque 1000 pedidos a 100ms + 50 a 5s dão média de 200ms mas escondem 50 utilizadores frustrados. Inclui tabela de decisão por tipo de sistema (checkout, API mobile, etc.).
  Link: https://one2n.io/blog/sre-math-percentiles-in-sre-why-averages-lie-about-latency
- Extra canónico: Google SRE Book, capítulo sobre SLOs - SLOs de latência devem ser baseados em percentis, não em médias.

**2. Ferramentas de carga k6 / wrk / ab:**
- MangoHost - "Use wrk2, ab, and k6 for Web Load Testing in Production" - compara: ab é single-thread, muito rápido para 1 URL estático; wrk/wrk2 é multi-threaded, event-loop, Lua, máximo RPS; k6 é moderno (Go+JS), scriptable para fluxos complexos, checks e CI. Inclui decision tree prático.
  Link: https://mangohost.net/blog/use-wrk2-ab-and-k6-for-web-load-testing-in-production/
- Docs oficiais: k6 https://k6.io/docs/ , ab https://httpd.apache.org/docs/2.4/programs/ab.html , wrk https://github.com/wg/wrk

Utilizar p50 para descrever o caso típico, p95 para afinacão de desempenho e p99 para expor gargalos e outliers. No relatório, apresentar sempre distribuição, não só média.

### Avaliação

*   D1 40% + D2 30% + D3 30% + Bónus 10% documentação reprodutível (limte 20 valores)
*   Critério de reprovação: não definir carga de forma científica ou não fazer teste de falha documentado.

---
*ITI 2025/2026 - Docente Henrique Santos - Percurso T-E*


---

### 🇬🇧 English

> **This guide complements the main README.md.** It is for students with Working Student status who work individually or in groups of 2, without weekly support. It keeps the 3 pillars of the regular project (compute, storage, distributed processing) but in a minimal 1-node architecture.

#### Context

Regular students work in groups of 6, with 2h/week class + 4h autonomous (5 ECTS), split into 3 phases. T-E students do not have that availability nor collaborative work. This project is a **single integrative phase**, estimated at 50-60h total.

Base architecture remains [ITI-Lab](https://github.com/hdsantos/ITI-Lab): Controller VM `192.168.57.10` with Ansible/Prometheus/Grafana + 1 Node `192.168.57.11` with Docker. See `docs/01-controlador.md` and `docs/02-no-referencia-e-clones.md`.

The application server is **pdfer** (`docker/pdfer-go` or `docker/pdfer-python`).

#### Target Architecture T-E (1 Node)

```
[Host] -> [Controller 57.10] --Ansible--> [Node 57.11 - Docker]
                                            ├── pdfer-1 (container :8080)
                                            ├── pdfer-2 (container :8081) - replica
                                            ├── nginx-proxy (container :80 -> pdfer-1/2)
                                            └── /mnt/pdfer-data -> NFS mount from TrueNAS
[TrueNAS VM 57.20 - 1 vCPU/2GB/2x10GB virtual disks in MIRROR]
```

**Key difference from regular students project:** No disk requested for distributed storage. T-E student creates 2 local 2GB virtual disks in VirtualBox and attaches them to TrueNAS VM. This ensures fault tolerance without group dependency. **NFS** is used instead of iSCSI - simpler, stateless, no LUN coordination needed.

#### Challenge 1 - Deploy and Monitoring (40%)

**Goal:** Equivalent to regular Phase 1.

1. Use Controller Ansible to install Docker on Node (`ansible/01-install-docker.yml`).
2. Deploy pdfer via `docker compose` (see `docs/03-pdfer2container.md`).
3. **Mandatory monitoring** (see `docs/04-monitorizacao.md`):
   *   Grafana dashboard with: Node CPU/Mem (Node Exporter), container CPU/Mem (cAdvisor), Prometheus targets state.
   *   Create 1 alert: `pdfer down` or `CPU > 80% for 2m`.

**Deliverable D1:** adjusted `docker-compose.yml`, screenshot of `http://192.168.57.10:3000` (Grafana) and `http://192.168.57.10:9090/targets`.

#### Challenge 2 - Fault-Tolerant NAS - NFS (30%)

**Goal:** Equivalent to regular Phase 2, but without iSCSI.

**Why NFS and not iSCSI for T-E:** iSCSI requires initiator/target and LUN management, which only makes sense with multiple nodes competing for same storage. For an isolated student, NFS is more realistic, simpler to debug and equally valid as fault-tolerant NAS.

**Steps:**

1. Create TrueNAS Core (or XigmaNAS) VM `192.168.57.20` with 2x20GB virtual disks, besides the system disk.
2. In TrueNAS:
   *   Storage > Pools > Create Pool > 2 disks in **Mirror** (equivalent to RAIDZ-1 concept for regulars, but feasible solo - 1 failure tolerated). Format as ZFS.
   *   Datasets > `pdfer-share` > Share Type: NFS
   *   Sharing > NFS Shares > Add, Path `/mnt/pool0/pdfer-share`, Maproot User `root`, Networks `192.168.57.0/24`
3. On Node `57.11`:
```bash
   sudo apt install nfs-common
   sudo mkdir -p /mnt/pdfer-data
   sudo mount -t nfs 192.168.57.20:/mnt/pool0/pdfer-share /mnt/pdfer-data
```
4. Change `compose.yaml` to use bind volume `/mnt/pdfer-data:/app/store`
5. **Reliability test:** In TrueNAS, Storage > Disks > Offline one disk. Run `zpool status` and show DEGRADED but ONLINE. Upload via pdfer and prove it still works. Then Online + Resilver.

**Deliverable D2:** Screenshots of `zpool status` healthy, DEGRADED and after resilver + NFS mount on node + Grafana I/O graph during failure.

#### Challenge 3 - Scalability and Failover with Reverse Proxy (30%)

1. On Node, run 2 pdfer replicas.
```yaml
   # compose.override para T-E
   services:
     pdfer-1: ... ports 8080
     pdfer-2: ... ports 8081
     nginx-proxy:
       image: nginx:alpine
       ports: ["80:80"]
       volumes: ["./nginx.conf:/etc/nginx/nginx.conf:ro"]
```
2. Configure through `nginx.conf`:
```
   upstream pdfer_cluster {
       server pdfer-1:8080 max_fails=2 fail_timeout=10s;
       server pdfer-2:8080 max_fails=2 fail_timeout=10s;
   }
   server { location / { proxy_pass http://pdfer_cluster; } }
```
3. **Failover test:** `docker stop pdfer-1` and prove via `curl http://192.168.57.11/files` service continues via pdfer-2. In Prometheus, show that the target pdfer-1 is down but the global service is up.

**Deliverable D3:** `nginx.conf`, `access.log` showing round-robin, and failover proof.

---

#### Scientific Definition of Workload for Metrics (MANDATORY for T-E)

To make metrics comparable, it's not enough to say "I tested with many files". You have to define the workload in a reproducible way. That's the point that will be most evaluated.

**Must define in report:**

1.  **Tool:** Use one for all tests: `k6`, `wrk` or `ab`. Recommended: `k6` (it has a reproducible JS script).
2.  **Load profiles (3 mandatory):**

| Profile | Description | Files | Size | Concurrency | Total Requests |
| :--- | :--- | :--- | :--- | :--- | :--- |
| S | Small objects | 100 files | 1-10 KB | 1, 10, 50 | 1000 |
| M | Medium objects | 20 files | 1 MB | 1, 10, 50 | 200 |
| L | Large objects | 5 files | 10 MB | 1, 10 | 50 |

3.  **Example reproducible k6 script (include in repo):**
    ```javascript
    // k6-load.js
    import http from 'k6/http';
    export let options = { vus: 10, duration: '30s' };
    export default function() {
      http.get('http://192.168.57.11/files');
    }
    ```

4.  **Metrics to report for each profile and each scenario (Local vs NFS vs NFS Degraded vs Cluster):**
    *   Latency: p50, p95, p99 (ms) - from k6
    *   Throughput: req/s and MB/s
    *   Errors: % failures
    *   System: Node and TrueNAS CPU%/Mem (Grafana), ZFS IOPS/latency (`zpool iostat 1`)

5.  **Mandatory comparison scenarios:**
    *   A) pdfer with local disk (baseline)
    *   B) pdfer with healthy NFS Mirror
    *   C) pdfer with DEGRADED NFS Mirror (1 disk offline)
    *   D) pdfer via Nginx with 1 replica down

Present in table. Eg: "Load M, VUs=10: Latency p95 A=120ms, B=180ms (+50%), C=210ms (+75%), D=130ms".

This allows for a scientific discussion of the network storage penalty and the tolerance gain.

---

#### Delivery and Evaluation

*   Git repo (fork of ITI-Lab) with `k6-load.js` + `nginx.conf` + final `compose.yaml` (or files sent by email)
*   Report 6-8 pages with architecture, load definition, metrics tables and failure tests
*   15 min oral discussion
*   Grading: D1 40% + D2 30% + D3 30% + Bonus 10% reproducible docs (limit 20)

#### Recommended Reading (for all students - workload definition and percentiles)

**1. p50/p95/p99 percentiles - why averages lie:**
- One2N - "Percentiles in SRE: Why averages lie about latency" - defines p50 as median (typical), p95 as early warning (5% slower) and p99 as critical tail. Shows why 1000x100ms + 50x5s = 200ms average hides user pain. Includes decision table per system type.
  Link: https://one2n.io/blog/sre-math-percentiles-in-sre-why-averages-lie-about-latency
- Canonical: Google SRE Book, SLO chapter - latency SLOs should be percentile-based.

**2. Load tools k6 / wrk / ab:**
- MangoHost - "Use wrk2, ab, and k6 for Web Load Testing in Production" - ab single-thread for single URL, wrk/wrk2 multi-threaded Lua max RPS, k6 modern Go+JS for complex flows and CI.
  Link: https://mangohost.net/blog/use-wrk2-ab-and-k6-for-web-load-testing-in-production/
- Official docs: k6 https://k6.io/docs/ , ab https://httpd.apache.org/docs/2.4/programs/ab.html , wrk https://github.com/wg/wrk

Use p50 for typical, p95 for tuning, p99 for bottlenecks. Always report distribution, not just average.

*   Fail criterion: not defining load scientifically or not documenting failure test.

---
*ITI 2025/2026 - Prof. Henrique Santos - T-E Path*
