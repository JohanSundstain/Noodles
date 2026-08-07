#!/bin/bash

echo "=== VLESS REALITY installer ==="

read -p "Порт [443]: " PORT
PORT=${PORT:-443}

echo ""
echo "Транспорт:"
echo "1) TCP"
echo "2) XHTTP"

read -p "Выбор [2]: " TRANSPORT
TRANSPORT=${TRANSPORT:-2}

case $TRANSPORT in

1)
NETWORK="tcp"
;;

2)
NETWORK="xhttp"
;;

*)
echo "Ошибка выбора"
exit 1
;;

esac

echo ""
echo "REALITY target:"
echo "1) Microsoft"
echo "2) Amazon"
echo "3) Samsung"
echo "4) Свой"

read -p "Выбор [1]: " TARGET_CHOICE
TARGET_CHOICE=${TARGET_CHOICE:-1}

case $TARGET_CHOICE in

1)
TARGET="www.microsoft.com:443"
SERVERNAME="www.microsoft.com"
;;

2)
TARGET="www.amazon.com:443"
SERVERNAME="www.amazon.com"
;;

3)
TARGET="www.samsung.com:443"
SERVERNAME="www.samsung.com"
;;

4)
read -p "Введите target (example.com:443): " TARGET
SERVERNAME=$(echo $TARGET | cut -d: -f1)
;;

*)
echo "Ошибка"
exit 1
;;

esac


echo ""
echo "Проверьте настройки:"
echo "Порт: $PORT"
echo "Пользователей: $USERS"
echo "Transport: $NETWORK"
echo "Target: $TARGET"

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
            "port": "$PORT",
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
                "network": "$NETWORK",
                "xhttpSettings": {
                    "path": "/"
                },
                "security": "reality",
                "realitySettings": {
                    "show": false,
                    "target": "$TARGET",
                    "serverNames": [
                        "$SERVERNAME"
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