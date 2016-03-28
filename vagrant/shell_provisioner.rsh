#!/usr/bin/env bash

set -e

function blue () { echo -e "\\033[34m$(cat)\\033[39m"; }
function cyan () { echo -e "\\033[36m$(cat)\\033[39m"; }
function green () { echo -e "\\033[32m$(cat)\\033[39m"; }
function magenta () { echo -e "\\033[35m$(cat)\\033[39m"; }
function red () { echo -e "\\033[31m$(cat)\\033[39m"; }

echo -e "\n"
echo "----------------------------------" | blue
echo "Reconfiguring the network settings"  | green
echo "----------------------------------" | blue
echo -e "\n"

[ -e /etc/init.d/network ] && INITD_NETWORK=network && COMMAND=restart
[ -e /etc/init.d/networking ] && INITD_NETWORK=networking && COMMAND=reload

sudo /etc/init.d/${INITD_NETWORK} ${COMMAND} &> /dev/null \
    && echo "- Network configuration reloaded" | cyan || echo "- Could not reload the network's configuration" | red

echo -e "\n"
echo "----------------------------------" | blue
echo "Syncing git and GitHub information"  | green
echo "----------------------------------" | blue
echo -e "\n"

echo " - Check file rights" | cyan
[ -e ~/.gitconfig ] && sudo chown vagrant.vagrant ~/.gitconfig
[ -e ~/.ssh/known_hosts ] && sudo chown vagrant.vagrant ~/.ssh/known_hosts

echo " - Synchronize your git configuration" | cyan
echo -e <%= AerisCloud::Environment::GITCONFIG.shellescape %> > ~/.gitconfig

echo " - Preset the GitHub public key in your known hosts" | cyan
grep -q -s github.com ~/.ssh/known_hosts || ssh-keyscan github.com >> ~/.ssh/known_hosts
sudo mkdir -p /root/.ssh
sudo touch /root/.ssh/known_hosts && sudo chmod 644 /root/.ssh/known_hosts
sudo grep -q -s github.com /root/.ssh/known_hosts || ssh-keyscan github.com | sudo tee -a /root/.ssh/known_hosts > /dev/null

if
    [ "<%= PROJECT.rsync? %>" == "true" ]
then
    sudo mkdir -p /data/<%= PROJECT.name %>
    sudo chown vagrant.vagrant /data/<%= PROJECT.name %>
fi

echo -e "\n"