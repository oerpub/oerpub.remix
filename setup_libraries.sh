#!/bin/bash

# a simple way to get the newest code.
getgit() {
    echo "=== Installing "$2" ===="
    if [ -e external/$2 ]; then
        pushd external/$2
        git pull
        popd
    else
        git clone --recursive $1 external/$2
    fi
}

# Sword library
getgit git://github.com/cscheffler/swordpush.git swordcnx

pushd swordpush/views/
ln -s ../../external/swordcnx .
popd
