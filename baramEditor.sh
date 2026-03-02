#!/usr/bin/env bash

SOURCE=${BASH_SOURCE[0]}

while [ -L "$SOURCE" ]; do
    DIR=$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )
    SOURCE=$(readlink "$SOURCE")
    [[ $SOURCE != /* ]] && SOURCE=$DIR/$SOURCE
done

cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1

source venv/bin/activate

python -m baramEditor.main
