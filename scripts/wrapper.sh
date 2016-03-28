#!/bin/bash
script="$1"
shebang=$(head -1 "$script")
interp=( ${shebang#\#!} )        # use an array in case a argument is there too
# now run
shift 1
exec "${interp[@]}" "$script" "${@}"
