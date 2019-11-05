#!/usr/bin/env bash

VENDOR_DIR="./vendor"
REQS="requirements.txt"
OUT="dist.`uuidgen`.zip"
SRCDIR="./src"


package_vendor_deps() {


    pipenv lock -r > $REQS
    pip install -r $REQS --no-deps -t $VENDOR_DIR
    rm $REQS

    pushd $VENDOR_DIR
    zip -r9 ${OLDPWD}/$OUT .
    popd
    rm -rf $VENDOR_DIR
}

add_src_to_archive() {
    pushd $SRCDIR
    zip -r9 ${OLDPWD}/$OUT .
    popd
}

package_vendor_deps
add_src_to_archive