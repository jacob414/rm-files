#!/bin/sh

scp $1.* rm2:/home/root/.local/share/remarkable/xochitl/
ssh rm2 chmod 644 /home/root/.local/share/remarkable/xochitl/$1.*
ssh rm2 systemctl restart xochitl
