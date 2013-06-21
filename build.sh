#!/bin/bash

: ${BINDIR:=$HOME/bin}
: ${DATADIR:=$HOME/.local/share}
: ${LOCALES:="fr"}

set -e

cd $(dirname $0)

function do_locales()
{
  messages=messages.pot
  echo "==> updating $messages"
  xgettext -k_ -kN_ --language=python --from-code=utf-8 -o $messages rembobine.py

  for locale in $LOCALES
  do
    if [[ -f $locale.po ]]
    then
      echo "==> updating $locale.po"
      msgmerge -U $locale.po $messages
    else
      echo "==> creating $locale.po"
      msginit --locale=$locale
    fi
  done
}

function do_install_locales()
{
  dir=$DATADIR/locale/$locale/LC_MESSAGES
  mkdir -p $dir
  for locale in $LOCALES
  do
    dest=$dir/rembobine.mo
    echo "==> creating $dest"
    # compile & install
    msgfmt $locale -o $dest
  done
}

function do_install_bin()
{
  dest=$BINDIR/rembobine
  echo "==> installing $dest"
  install -D rembobine.py $dest
  echo "    make sure to add $BINDIR to your PATH environment variable"
}

function do_install_desktop()
{
  dir=$DATADIR/applications
  dest=$dir/rembobine.desktop
  echo "==> creating $dest"
  mkdir -p $dir
  sed 's;__BINDIR__;'"$BINDIR"';' rembobine.desktop > $dest
}

function do_install()
{
  do_install_bin
  do_install_desktop
  do_install_locales
}

if [[ -z "$1" ]]
then
  echo "usage: $(basename $0) {install|locales}"
  exit 1
fi

for arg in "$*"
do
  do_$arg
done
