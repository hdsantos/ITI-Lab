# Lab Ansible + Docker + Monitoring — Parte 3: Executar o PDFer num contentor

Este guia descreve como colocar o servidor **PDFer** a funcionar num contentor Docker no `node1` do laboratório criado nas partes anteriores.

O `node1` já deverá ter:

- Ubuntu Server instalado;
- endereço `192.168.57.11` na rede Host-only;
- acesso SSH com o utilizador `itiusr`;
- Docker Engine e Docker Compose instalados pelo playbook `01-Install-Docker.yml`.

Não é necessário instalar Go nem compilar o programa. O servidor é fornecido como um executável Linux denominado `pdfer`.

## 1. Funcionamento do PDFer

O PDFer é o servidor Web que será utilizado como base nos trabalhos da unidade curricular. Escuta na porta TCP `8080` e disponibiliza três operações principais:

| Método | Endpoint | Operação |
|---|---|---|
| `GET` | `/files` | Devolve a lista dos ficheiros armazenados |
| `POST` | `/files` | Cria e cifra um novo ficheiro |
| `GET` | `/files/{fileId}` | Decifra e devolve o ficheiro indicado |

O `POST /files` recebe no corpo do pedido:

- `key`: chave utilizada para cifrar o ficheiro;
- `length`: número de caracteres do ficheiro;
- `fileName`: nome atribuído ao ficheiro.

O `GET /files/{fileId}` recebe no corpo do pedido:

- `key`: chave utilizada para decifrar o ficheiro.

O servidor utiliza uma pasta chamada `store`, localizada no seu diretório de execução. Essa pasta contém os ficheiros cifrados e deverá persistir mesmo que o contentor seja removido ou substituído.

O código-fonte não é necessário para realizar o trabalho. Caso uma equipa pretenda alterar o servidor para implementar uma funcionalidade ou otimização, deverá solicitar o código-fonte ao docente e discutir previamente a alteração proposta.

## 2. Preparar o diretório no `node1`

A partir do controlador, confirmar primeiro a ligação ao nó:

```bash
ssh itiusr@192.168.57.11
```

No `node1`, criar o diretório do projeto e a pasta de armazenamento:

```bash
mkdir -p ~/pdfer-lab/store
exit
```

Copiar o executável fornecido para o nó:

```bash
scp pdfer itiusr@192.168.57.11:~/pdfer-lab/
```

Copiar também o ficheiro `compose.yaml` disponibilizado com este guia:

```bash
scp compose.yaml itiusr@192.168.57.11:~/pdfer-lab/
```

No final, o diretório deverá apresentar esta estrutura:

```text
pdfer-lab/
├── pdfer
├── Dockerfile
├── compose.yaml
└── store/
```

O `Dockerfile` será criado no passo seguinte.

## 3. Criar o `Dockerfile`

Ligar novamente ao nó e entrar no diretório do projeto:

```bash
ssh itiusr@192.168.57.11
cd ~/pdfer-lab
nano Dockerfile
```

Introduzir o conteúdo seguinte:

```dockerfile
FROM ubuntu:26.04

WORKDIR /app

COPY pdfer /app/pdfer

RUN chmod +x /app/pdfer \
    && mkdir -p /app/store

EXPOSE 8080

ENTRYPOINT ["/app/pdfer"]
```

Este ficheiro estabelece que:

- a imagem é baseada em Ubuntu Linux;
- o diretório de execução do servidor é `/app`;
- o executável é copiado para `/app/pdfer`;
- a pasta esperada pelo programa é `/app/store`;
- o servidor utiliza a porta 8080;
- o PDFer é iniciado automaticamente quando o contentor arranca.

## 4. Verificar o `compose.yaml`

O ficheiro fornecido contém:

```yaml
services:
  pdfer:
    build:
      context: .
      dockerfile: Dockerfile
    image: iti/pdfer:1.0
    container_name: pdfer
    ports:
      - "8080:8080"
    volumes:
      - ./store:/app/store
    restart: unless-stopped
```

A montagem `./store:/app/store` associa a pasta `store` do nó à pasta utilizada pelo servidor dentro do contentor. Deste modo:

- os ficheiros permanecem no nó se o contentor for removido;
- é possível observar diretamente os ficheiros cifrados;
- uma nova versão do contentor pode reutilizar os dados existentes.

## 5. Construir a imagem e iniciar o contentor

No `node1`, dentro de `~/pdfer-lab`:

```bash
docker compose up --build -d
```

O comando constrói a imagem `iti/pdfer:1.0`, cria o contentor e inicia o servidor em segundo plano.

Verificar o estado:

```bash
docker compose ps
```

Consultar os logs:

```bash
docker compose logs pdfer
```

Se for necessário acompanhar continuamente os logs:

```bash
docker compose logs -f pdfer
```

## 6. Testar o servidor

### 6.1 Listar os ficheiros

No próprio `node1`:

```bash
curl http://localhost:8080/files
```

Ou a partir do controlador:

```bash
curl http://192.168.57.11:8080/files
```

### 6.2 Criar um ficheiro cifrado

```bash
curl -X POST http://192.168.57.11:8080/files \
  -H "Content-Type: application/json" \
  -d '{
    "key": "chave-de-teste",
    "length": 1000,
    "fileName": "teste.txt"
  }'
```

Confirmar que foi criado um ficheiro na pasta do nó:

```bash
ls -lh ~/pdfer-lab/store
```

O conteúdo guardado deverá estar cifrado e, por isso, não deverá corresponder ao conteúdo devolvido pelo servidor após decifragem.

### 6.3 Recuperar e decifrar um ficheiro

Substituir `teste.txt` pelo identificador devolvido pelo servidor, caso seja diferente:

```bash
curl -X GET http://192.168.57.11:8080/files/teste.txt \
  -H "Content-Type: application/json" \
  -d '{"key":"chave-de-teste"}'
```

## 7. Parar e voltar a criar o contentor

Parar e remover o contentor:

```bash
docker compose down
```

Confirmar que os ficheiros continuam no nó:

```bash
ls -lh store
```

Voltar a criar o contentor:

```bash
docker compose up -d
```

Os ficheiros deverão voltar a estar disponíveis através do servidor. Esta experiência demonstra a diferença entre o ciclo de vida do contentor e a persistência dos dados.

Para reconstruir a imagem depois de substituir o executável ou alterar o `Dockerfile`:

```bash
docker compose up --build -d
```

## 8. Verificações finais

Antes de considerar esta etapa concluída, confirmar que:

- `docker compose ps` mostra o contentor `pdfer` em execução;
- `GET /files` responde a partir do controlador;
- `POST /files` cria um ficheiro na pasta `store` do nó;
- `GET /files/{fileId}` devolve o conteúdo quando é utilizada a chave correta;
- os dados permanecem depois de executar `docker compose down` e `docker compose up -d`;
- não foi necessário iniciar o executável manualmente dentro do contentor.

## Troubleshooting

| Sintoma | Causa provável | Solução |
|---|---|---|
| `permission denied` ao construir a imagem | O executável não tem permissões adequadas | Confirmar o `RUN chmod +x /app/pdfer` no `Dockerfile` |
| `exec format error` | Executável para outro sistema operativo ou arquitetura | Confirmar que foi usado o executável Linux adequado à arquitetura da VM |
| `No such file or directory` ao iniciar | Executável incompatível com as bibliotecas da imagem ou nome incorreto | Confirmar o nome `pdfer`; comunicar o erro ao docente |
| Porta 8080 já em utilização | Outro processo ou contentor está a usar a porta | Executar `sudo ss -ltnp | grep :8080` e parar o serviço anterior |
| Servidor responde no nó, mas não no controlador | Contentor parado, porta não publicada ou problema de rede | Verificar `docker compose ps`, `docker compose logs pdfer` e `ping 192.168.57.11` |
| Ficheiros não aparecem em `store` | Volume montado no caminho errado | Confirmar `./store:/app/store` e executar o Compose a partir de `~/pdfer-lab` |
| `docker: permission denied` | A sessão ainda não reconhece a pertença ao grupo `docker` | Terminar a sessão SSH e voltar a entrar, ou executar `newgrp docker` |

