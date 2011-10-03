#!/bin/bash

# a simple way to get the newest code.
getgit() {
    echo "=== Installing "$2" ===="
    if [ -e $2 ]; then
        pushd $2
        git pull
        popd
    else
        git clone --recursive $1 $2
    fi
}

pushd external

# Sword library
getgit git://github.com/cscheffler/swordpush.git swordcnx

# rhaptos.cnxmlutils for doc conversion
getgit git://github.com/rochecompaan/rhaptos.cnxmlutils.git cnxmlutils

popd

pushd swordpush/views/
ln -s ../../external/swordcnx .
popd
