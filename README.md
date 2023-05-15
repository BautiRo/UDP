# Intro-2C22-g8-tp1
Repositorio para el TP 1 de Introduccion a los sistemas distribuidos

## Server
Para iniciar el servidor:

```sh
python start - server -h
usage : start - server [ - h ] [ - v | -q ] [ - H ADDR ] [ - p PORT ] [ - s DIRPATH ]

< command description >

optional arguments :
-h , -- help    [show this help message and exit]
-v , -- verbose [increase output verbosity]
-q , -- quiet   [decrease output verbosity]
-H , -- host    [service IP address]
-p , -- port    [service port]
-s , -- storage [storage dir path]
```

### Ejemplo:
```sh
python3 start-server.py -H localhost -p 8888 -s server_files -v
python3 start-server-go-back-n.py -H localhost -p 8888 -s server_files -v
```

## Client - Upload
Para subir un archivo al servidor:

```sh
python upload -h
usage : upload [ - h ] [ - v | -q ] [ - H ADDR ] [ - p PORT ] [ - s FILEPATH ] [ - n FILENAME ]

< command description >

optional arguments :
-h , -- help    [show this help message and exit]
-v , -- verbose [increase output verbosity]
-q , -- quiet   [decrease output verbosity]
-H , -- host    [server IP address]
-p , -- port    [server port]
-s , -- src     [source file path]
-n , -- name    [file name]
```

### Ejemplo:
```sh
python3 upload.py -H localhost -p 8888 -n test_doc.pdf -s client_files -v
python3 upload-go-back-n.py -H localhost -p 8888 -n test_doc.pdf -s client_files -v
```
## Test - Upload
Para probar varios clientes juntos:
```sh
client_test_upload
client_test_upload_go_back_n
```
## Client - Download
Para descargar un archivo del servidor:

```sh
python download -h
usage : download [ - h ] [ - v | -q ] [ - H ADDR ] [ - p PORT ] [ - d FILEPATH ] [ - n FILENAME ]

< command description >

optional arguments :
-h , -- help    [show this help message and exit]
-v , -- verbose [increase output verbosity]
-q , -- quiet   [decrease output verbosity]
-H , -- host    [server IP address]
-p , -- port    [server port]
-d , -- dst     [destination file path]
-n , -- name    [file name]
```

### Ejemplo:
```sh
python3 download.py -H localhost -p 8888 -n test_doc.pdf -d client_files -v
python3 download-go-back-n.py -H localhost -p 8888 -n test_doc.pdf -d client_files -v
```
## Test - Download
Para probar varios clientes juntos:
```sh
client_test_download
client_test_download_go_back_n
```