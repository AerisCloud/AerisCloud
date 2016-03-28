#!/usr/bin/env bash

if [ ! -z ${BASH_SOURCE[0]} ]; then
    ac_script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
else
    ac_script_dir="$( cd "$( dirname "${0}" )" && pwd )"
fi

ac_root_dir="${ac_script_dir}/.."

# Cleanup
declare -f aeris &>/dev/null && unset -f aeris || true
declare -f cloud &>/dev/null && unset -f cloud || true

# This is a hook that allows aeris to be executed in the
# same shell instead of in a subshell
__ac_run () {
    cmd=${1}
    shift

    # portable way to create a tmp file on both OSX and Linux
    export AERIS_CD_TMP_FILE=$( mktemp -t aeris.cd.XXXXXX )

    # run the command
    ${ac_root_dir}/venv/bin/${cmd} "${@}"
    RES=$?

    # cd if cmd successful and dest set
    if [[ "${?}" == "0" ]]; then
        AERIS_DEST_PATH=$( cat "${AERIS_CD_TMP_FILE}" )

        if    [ ! -z "${AERIS_DEST_PATH}" ]\
           && [ -d "${AERIS_DEST_PATH}" ]; then
            cd "${AERIS_DEST_PATH}"
        fi

        unset AERIS_DEST_PATH
    fi

    # delete once done
    rm -f "${AERIS_CD_TMP_FILE}"
    unset AERIS_CD_TMP_FILE

    return ${RES}
}

aeris () {
    __ac_run "aeris" ${@}
}

cloud () {
    __ac_run "cloud" ${@}
}

export PATH="${ac_root_dir}/bin:${PATH}"

# autocomplete
if [ -f "${ac_script_dir}/complete.sh" ]; then
    [[ -n "${ZSH_NAME}" ]] && autoload bashcompinit && bashcompinit
    source "${ac_script_dir}/complete.sh"
fi
