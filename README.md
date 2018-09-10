[Steam-Key](https://github.com/zyfworks/steam-key) 的 Python 移植


#### 安装 `uWSGI`

只支持 `uWSGI` 作为 web server, `uWSGI` 需要 `OpenSSL` 才能支持 `WebSocket`, 所以要从源码安装 `uWSGI`

```shell
sudo apt-get install build-essential python3-dev libssl-dev
pip3 install uwsgi -Iv --no-cache-dir --no-binary all 
```

#### 调试

```shell
uwsgi --http :9090 --http-websockets --wsgi main:app --master --gevent \
    --set-placeholder SERVER_NAME=test --set-placeholder DEBUG=true --python-auto-reload 1
```

或者使用配置文件, 在配置中添加 `DEBUG=true` 标志

#### 部署

使用 Nginx 作为前端反代, uwsgi 监听在 `9090` 端口

uwsgi 配置示例 `config.ini`

```
# 程序目录
base = /path_to/steam-key-python

# 如果使用 virtualenv, 需要设置其目录
home = %(base)/venv
pythonpath = %(base)

# wsgi 入口
module = main
callable = app

# 使用 uwsgi 协议
socket = 127.0.0.1:9090
http-websockets = true

# 并发数
gevent = 100
master = true

# 服务器名
SERVER_NAME = 测试

```

运行 `uwsgi --ini config.ini`

nginx 配置示例

```shell
location / {
   uwsgi_pass 127.0.0.1:9090;
   include uwsgi_params;
}
```



### License
Apache License
