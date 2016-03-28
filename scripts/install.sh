#!/usr/bin/env bash

# colors
bold="$( tput bold )"
cred="$( tput setaf 1 )"
cgrn="$( tput setaf 2 )"
cylw="$( tput setaf 3 )"
cblu="$( tput setaf 4 )"
crst="$( tput sgr0 )"

# some useful variables
if [[ -z "${GIT_REPO}" ]]; then
    GIT_REPO="git@github.com:aeriscloud/aeriscloud.git"
fi

if [[ -z "${GIT_BRANCH}" ]]; then
    GIT_BRANCH="master"
fi

if [ -z "${INSTALL_DIR}" ]; then
    INSTALL_DIR="$(pwd)"
fi

if [[ -z "${OS_FAMILY}" ]]; then
    OS_FAMILY="$(uname -s)"
fi

if [[ -z "${DEBUG}" ]]; then
    DEBUG=0
fi

auto_log_file=0
if [[ -z "${SETUP_LOG}" ]]; then
    auto_log_file=1
    SETUP_LOG="$( mktemp -t aeris.setup.XXXX )"
fi

if [[ ${#@} -eq 1 ]] && [[ "${1}" == '-h' ]]; then
    echo "${cblu}Usage:${crst} ${bold}${0}${crst}

  Install AerisCloud on your computer

${cblu}Environment variables:${crst}
  ${bold}GIT_REPO${crst}     ${GIT_REPO}
  ${bold}GIT_BRANCH${crst}   ${GIT_BRANCH}
  ${bold}INSTALL_DIR${crst}  ${INSTALL_DIR}
  ${bold}OS_FAMILY${crst}    ${OS_FAMILY}
  ${bold}SETUP_LOG${crst}    Random file in ${TMPDIR}

${cblu}Extra Informations:${crst}
  ${bold}OS_FAMILY${crst} is automatically determined if not set so it should not be
            necessary to override this variable.
  ${bold}SETUP_LOG${crst} is set automatically to a random file in your operating system's
            tmp folder and is automatically deleted if the script is
            successful. If you want to keep the log file on success, just
            override this variable.
"
    exit
fi

# utility functions
function confirm {
    local CONFIRM_MSG REPLY

    CONFIRM_MSG="${1}"
    [[ -z "${CONFIRM_MSG}" ]] && CONFIRM_MSG="Continue"
    read -p "${CONFIRM_MSG} (Y/n) " -n 1
    [[ ! -z "${REPLY}" ]] && echo ""
    echo ""
    [[ "${REPLY}" == "n" ]] || [[ "${REPLY}" == "N" ]] && return 1
    return 0
}

function age {
    echo $(( $(date +%s) - $( stat -f %m "${1}" ) ))
}

function chksum {
    hash shasum 2>/dev/null && shasum "${1}" | cut -d ' ' -f 1 && return
    hash md5sum 2>/dev/null && md5sum "${1}" | cut -d ' ' -f 1 && return
    stat -f %m "${1}"
}

# shamelessly stolen from https://github.com/cloudflare/semver_bash
function semverParseInto() {
    local RE='[^0-9]*\([0-9]*\)[.]\([0-9]*\)[.]\([0-9]*\)\([0-9A-Za-z-]*\)'
    #MAJOR
    eval $2=`echo $1 | sed -e "s#$RE#\1#"`
    #MINOR
    eval $3=`echo $1 | sed -e "s#$RE#\2#"`
    #MINOR
    eval $4=`echo $1 | sed -e "s#$RE#\3#"`
    #SPECIAL
    eval $5=`echo $1 | sed -e "s#$RE#\4#"`
}

function semverLT() {
    local MAJOR_A=0
    local MINOR_A=0
    local PATCH_A=0
    local SPECIAL_A=0

    local MAJOR_B=0
    local MINOR_B=0
    local PATCH_B=0
    local SPECIAL_B=0

    semverParseInto $1 MAJOR_A MINOR_A PATCH_A SPECIAL_A
    semverParseInto $2 MAJOR_B MINOR_B PATCH_B SPECIAL_B

    if [ $MAJOR_A -lt $MAJOR_B ]; then
        return 0
    fi

    if [[ $MAJOR_A -le $MAJOR_B  && $MINOR_A -lt $MINOR_B ]]; then
        return 0
    fi

    if [[ $MAJOR_A -le $MAJOR_B  && $MINOR_A -le $MINOR_B && $PATCH_A -lt $PATCH_B ]]; then
        return 0
    fi

    if [[ "_$SPECIAL_A"  == "_" ]] && [[ "_$SPECIAL_B"  == "_" ]] ; then
        return 1
    fi
    if [[ "_$SPECIAL_A"  == "_" ]] && [[ "_$SPECIAL_B"  != "_" ]] ; then
        return 1
    fi
    if [[ "_$SPECIAL_A"  != "_" ]] && [[ "_$SPECIAL_B"  == "_" ]] ; then
        return 0
    fi

    if [[ "_$SPECIAL_A" < "_$SPECIAL_B" ]]; then
        return 0
    fi

    return 1

}

# install step mechanism
step_current_msg=""
step_prev_trace_setting=""
step_is_prompt=0

function step_set_trap {
    step_prev_trace_setting=$(set +o | grep errtrace)
    set -o errtrace
    trap 'step_failure' ERR
}

function step_unset_trap {
    trap - ERR
    eval ${step_prev_trace_setting}
    unset step_prev_trace_setting
}

function step {
    step_current_msg="${1}"

    if [[ ${#@} -eq 2 ]]; then
        echo -en "${1} [${2}] ... ${cylw}RUNNING${crst}"
    else
        echo -en "${1} ... ${cylw}RUNNING${crst}"
    fi

    step_set_trap
}

function step_run {
    step_is_prompt=0

    if [[ $DEBUG -eq 0 ]]; then
        echo -e "\n>>> ${@}\n" >> ${SETUP_LOG}
        AC_NO_ASSISTANT=1 "${@}" >> ${SETUP_LOG} 2>&1
    else
        echo -e "\n>>> ${@}\n" | tee -a ${SETUP_LOG}
        AC_NO_ASSISTANT=1 "${@}" | tee -a ${SETUP_LOG}
    fi
}

function step_run_awk {
    step_is_prompt=0

    if [[ $DEBUG -eq 0 ]]; then
        echo -e "\n>>> ${@:3}\n" >> ${SETUP_LOG}
        AC_NO_ASSISTANT=1 "${@:3}" 2>&1 | tee -a ${SETUP_LOG} | awk "/${1}/{ printf \"\r\033[K${step_current_msg} [%s] ... ${cylw}RUNNING${crst}\", ${2}; fflush() }"
    else
        # forget the awk in debug mode
        echo -e "\n>>> ${@:3}\n" | tee -a ${SETUP_LOG}
        AC_NO_ASSISTANT=1 "${@:3}" | tee -a ${SETUP_LOG}
    fi
}

function step_run_prompt {
    step_is_prompt=1
    if [[ $DEBUG -eq 0 ]]; then
        echo -e "\n>>> ${@}\n" >> ${SETUP_LOG}
        echo ""
        AC_NO_ASSISTANT=1 "${@}" >> ${SETUP_LOG} 2>&1
    else
        echo -e "\n>>> ${@}\n" | tee -a ${SETUP_LOG}
        AC_NO_ASSISTANT=1 "${@}" | tee -a ${SETUP_LOG}
    fi
}

function step_warning {
    step_unset_trap

    if [[ ${DEBUG} -eq 1 ]]; then
        echo ""
    fi

    echo -e "\r\033[K${step_current_msg} ... ${cylw}WARNING${crst}
${1}
"
}

function step_skip {
    step_unset_trap

    if [[ ${DEBUG} -eq 1 ]]; then
        echo ""
    fi

    echo -e "\r\033[K${step_current_msg} ... ${cblu}SKIP${crst}"
}

function step_success {
    step_unset_trap

    # move back up if a prompt happened and reprint title
    if [[ ${DEBUG} -eq 1 ]]; then
        echo ""
    elif [[ ${step_is_prompt} -eq 1 ]]; then
        echo -ne "\033[2A"
    fi

    echo -e "\r\033[K${step_current_msg} ... ${cgrn}SUCCESS${crst}"
}

function step_fail_with {
    step_unset_trap

    echo -e "\r\033[K${step_current_msg} ... ${cred}FAILED${crst}

${1}

Consult ${cblu}${SETUP_LOG}${crst} for more details about the installation."
    exit 1
}

function step_failure {
    step_unset_trap

    if [[ ${DEBUG} -eq 1 ]]; then
        echo ""
    elif [[ ${step_is_prompt} -eq 1 ]]; then
        echo -ne "\033[2A\033[K"
    fi
    echo -e "\r${step_current_msg} ... ${cred}FAILED${crst}

Consult ${cblu}${SETUP_LOG}${crst} for details of what failed and where."
    exit 1
}

# start setup

echo -e "${cylw}
    ___             _      ________                __
   /   | ___  _____(_)____/ ____/ /___  __  ______/ /
  / /| |/ _ \/ ___/ / ___/ /   / / __ \/ / / / __  /
 / ___ /  __/ /  / (__  ) /___/ / /_/ / /_/ / /_/ /
/_/  |_\___/_/  /_/____/\____/_/\____/\__,_/\__,_/
${crst}
Welcome to the AerisCloud installer script.

This script may ask for your password several times during the course of the
setup to run steps that need administrator access.

Install directory: ${cblu}${INSTALL_DIR}${crst}
"

if ! confirm; then
    echo "Installation aborted."
    exit 1
fi

# Make sure that xcode tools are available on OSX
if [[ "${OS_FAMILY}" == "Darwin" ]]; then
    if ! xcode-select -p 1>/dev/null 2>&1; then
        echo -e "
Installing OSX Command Line Tools.

In the opening window please click \"Install\", accept the license agreement
and let the install run until the end before continuing.
"
        xcode-select --install 1>/dev/null 2>&1

        ROT=0
        while ! xcode-select -p 1>/dev/null 2>&1; do
            echo -en "\rInstalling XCode Tools ... "
            
            ROT=$(( $ROT + 1 ))
            case $ROT in
                1)
                    echo -n "|"
                    ;;
                2)
                    echo -n "/"
                    ;;
                3)
                    echo -n "-"
                    ;;
                4)
                    echo -n "\\"
                    ROT=0
                    ;;
            esac
            sleep 0.6
        done
	echo -e "Installing XCode Tools ... ${cgrn}SUCCESS${crst}\n"
    fi
fi

step "Creating install directory [${INSTALL_DIR}]"
if [[ ! -d "${INSTALL_DIR}" ]]; then
    step_run_prompt sudo -k -p "sudo password:" sh -c "mkdir -p '${INSTALL_DIR}' && chown $( id -un ):$( id -gn ) '${INSTALL_DIR}'"
    step_success
else
    step_skip
fi

skip_update=0
step "Cloning AerisCloud repository [${GIT_REPO}]"
if [[ ! -d "${INSTALL_DIR}/.git" ]]; then
    skip_update=1
    step_run git clone "${GIT_REPO}" "${INSTALL_DIR}"
    step_success
else
    step_skip
fi

cd "${INSTALL_DIR}"

# check if repo is dirty
step "Check if repository is clean"
step_run git diff-index --quiet HEAD
step_success

step "Updating to latest AerisCloud"
current_repo=$( git remote -v | grep '^origin' | grep 'fetch.$' | awk '{ print $2 }' )
if [[ "${current_repo}" != "${GIT_REPO}" ]]; then
    step_run git remote set-url origin ${GIT_REPO}
    step_run git fetch origin
fi
step_run git checkout "${GIT_BRANCH}"
if [[ ${skip_update} -eq 0 ]]; then
    step_run git pull
    step_success
else
    step_skip
fi

step "Installing python and ansible deps" ""
if [[ "${OS_FAMILY}" == "Darwin" ]]; then
    if ! hash easy_install 2>/dev/null; then
        step_fail_with "Python is not correctly setup on your system, please install Python 2.7 before proceeding"
    fi

    if ! hash virtualenv 2>/dev/null; then
        # install virtualenv
        step_run_prompt sudo -k -p "sudo password:" sh -c "easy_install virtualenv"
    fi
elif [[ "${OS_FAMILY}" == "Linux" ]]; then
    # there are too many linuxes out there, fail hard if virtualenv is not found
    if ! hash virtualenv 2>/dev/null && ! hash virtualenv2 2>/dev/null; then
        step_fail_with "Virtualenv is not installed on your system, please install it before proceeding (make sure to install the python2 version of Virtualenv)"
    fi
fi
step_run_awk 'Running' '$5' make deps
step_run_awk 'Running' '$5' make build
step_success

step "Check if VirtualBox is installed and up-to-date"
if hash VBoxManage 2>/dev/null; then
    required_vbox_version=$( grep virtualbox_version "${INSTALL_DIR}/scripts/install/inventory" | cut -d '=' -f 2 | tr -d '" ' )
    current_vbox_version=$( VBoxManage --version | grep -Eo "[0-9]+\.[0-9]+\.[0-9]+" )

    skip_vbox=1
    # check if we need to update virtualbox
    if semverLT "${current_vbox_version}" "${required_vbox_version}"; then
        skip_vbox=0
    fi

    if [[ ${skip_vbox} -eq 1 ]]; then
        step_skip
    else
        step_success
    fi
else
     step_fail_with "VirtualBox has not been found.
Make sure to install it.
You can download it from the website: https://www.virtualbox.org/wiki/Downloads/.
"
fi

step "Check if Vagrant is installed and up-to-date"
if hash vagrant 2>/dev/null; then
    required_vagrant_version=$( grep vagrant_version "${INSTALL_DIR}/scripts/install/inventory" | cut -d '=' -f 2 | tr -d '" ' )
    current_vagrant_version=$( vagrant --version | grep -Eo "[0-9]+\.[0-9]+\.[0-9]+" )

    skip_vagrant=1
    if semverLT "${current_vagrant_version}" "${required_vagrant_version}"; then
        skip_vagrant=0
    fi

    step_run vagrant plugin install vagrant-persistent-storage
    step_run vagrant plugin install vagrant-triggers

    if [[ ${skip_vagrant} -eq 1 ]]; then
        step_skip
    else
        step_success
    fi
else
    step_fail_with "Vagrant has not been found.
Make sure to install it.
You can download it from the website: https://www.vagrantup.com/downloads.html.
"
fi

step "Running ansible playbook"
pushd "${INSTALL_DIR}/scripts/install" &>/dev/null
step_run_prompt "${INSTALL_DIR}/venv/bin/ansible-playbook" --ask-sudo-pass -i inventory --connection=local install.yml
popd &>/dev/null
step_success

# clean automatically generated log files
step "Cleaning up"
if [[ ${auto_log_file} -eq 1 ]]; then
    step_run rm "${SETUP_LOG}"
    step_success
else
    step_skip
fi

echo

# Show the installed version of stuff, will also trigger the config assistant
# if necessary
"${INSTALL_DIR}/venv/bin/aeris" version

echo -e "\nInstallation finished successfully\n"
