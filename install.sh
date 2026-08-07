#!/bin/bash

echo "=== VLESS REALITY XHTTP installer ==="

read -p "Порт [443]: " PORT
export port=${PORT:-443}
export network="xhttp"

echo ""
echo "XHTTP mode:"
echo "1) auto"
echo "2) packet-up"
echo "3) stream-up"
read -p "Выбор [auto]: " XHTTP_MODE
XHTTP_MODE=${XHTTP_MODE:-1}

case $XHTTP_MODE in
    1)
    export mode="auto"
    ;;

    2)
    export mode="packet-up"
    ;;

    3)
    export mode="stream-up"
    ;;

    *)
    echo "Ошибка выбора mode"
    exit 1
    ;;
esac

read -p "Введите target [github.com:443]: " TARGET
export target=${TARGET:-"github.com:443"}
export serverName=$(echo $targer | cut -d: -f1)

echo ""
echo "Проверьте настройки:"
echo "Порт: $port"
echo "XHTTP MODE:" $mode
echo "Target: $target"

read -p "Готово? [Y/n]: " CONFIRM

if [[ "$CONFIRM" == "n" || "$CONFIRM" == "N" ]]; then
    exit 0
fi

echo "=== Будет установлен Xray ==="
sleep 3
apt update
apt install qrencode curl jq -y

# Включаем bbr
bbr=$(sysctl -a | grep net.ipv4.tcp_congestion_control)
if [ "$bbr" = "net.ipv4.tcp_congestion_control = bbr" ]; then
	echo "bbr уже включен"
else
	echo "net.core.default_qdisc=fq" >> /etc/sysctl.conf
	echo "net.ipv4.tcp_congestion_control=bbr" >> /etc/sysctl.conf
	sysctl -p
	echo "bbr включен"
fi

# Устанавливаем ядро Xray
bash -c "$(curl -4 -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install
[ -f /usr/local/etc/xray/.keys ] && rm /usr/local/etc/xray/.keys
touch /usr/local/etc/xray/.keys
echo "shortsid: $(openssl rand -hex 8)" >> /usr/local/etc/xray/.keys
echo "uuid: $(xray uuid)" >> /usr/local/etc/xray/.keys
xray x25519 >> /usr/local/etc/xray/.keys

export uuid=$(cat /usr/local/etc/xray/.keys | awk -F': ' '/uuid/ {print $2}')
export privatkey=$(cat /usr/local/etc/xray/.keys | awk -F': ' '/PrivateKey/ {print $2}')
export shortsid=$(cat /usr/local/etc/xray/.keys | awk -F': ' '/shortsid/ {print $2}')
export pbk=$(cat /usr/local/etc/xray/.keys | awk -F': ' '/PublicKey/ {print $2}')

# Создаем файл конфигурации Xray
touch /usr/local/etc/xray/config.json
cat << EOF > /usr/local/etc/xray/config.json
{
    "log": {
        "loglevel": "warning"
    },
    "routing": {
        "domainStrategy": "IPIfNonMatch",
        "rules": [
            {
                "type": "field",
                "domain": [
                    "geosite:category-ads-all"
                ],
                "outboundTag": "block"
            },
            {
                "type": "field",
                "ip": [
                    "geoip:cn"
                ],
                "outboundTag": "block"
            }
        ]
    },
    "inbounds": [
        {
            "listen": "0.0.0.0",
            "port": "$port",
            "protocol": "vless",
            "settings": {
                "clients": [
                    {
                        "email": "main",
                        "id": "$uuid",
                        "flow": ""
                    }
                ],
                "decryption": "none"
            },
            "streamSettings": {
                "network": "$netwoer",
                "xhttpSettings": {
                    "path": "/",
					"mode": "$mode"
                },
                "security": "reality",
                "realitySettings": {
                    "show": false,
                    "target": "$target",
                    "serverNames": [
                        "$serverName"
					],
                    "privateKey": "$privatkey",
                    "minClientVer": "",
                    "maxClientVer": "",
                    "maxTimeDiff": 0,
                    "shortIds": [
                        "$shortsid"
                    ]
                }
            },
            "sniffing": {
                "enabled": true,
                "destOverride": [
                    "http",
                    "tls",
                    "quic"
                ]
            }
        }
    ],
    "outbounds": [
        {
            "protocol": "freedom",
            "tag": "direct"
        },
        {
            "protocol": "blackhole",
            "tag": "block"
        }
    ],
    "policy": {
        "levels": {
            "0": {
                "handshake": 3,
                "connIdle": 180
            }
        }
    }
}
EOF

systemctl restart xray
echo "=== Xray-core успешно установлен ==="

echo "Установка Python, pip и venv..."
apt install -y python3 python3-pip python3-venv

echo "Создание виртуального окружения..."
python3 -m venv venv

echo "Активация виртуального окружения..."
source venv/bin/activate

echo "Обновление pip..."
python -m pip install --upgrade pip

echo "Установка зависимостей..."
pip install -r requirements.txt

echo "Установка vim"
apt install vim -y

echo "Установка tmux"
apt install tmux -y

echo "Установка htop"
apt install htop -y

echo "====================================="
echo "Установка завершена!"
echo "====================================="

# Создаем файл с подсказками
touch $HOME/help
cat << EOF > $HOME/help
Файл конфигурации находится по адресу:
    /usr/local/etc/xray/config.json
Публичный ключ:
	$pbk
Команда для перезагрузки ядра Xray:
    systemctl restart xray
EOF