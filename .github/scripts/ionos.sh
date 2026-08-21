#!/usr/bin/env bash
# Shared SFTP helpers for the sync workflow. Source this, don't execute it.
#
# Requires IONOS_USER, IONOS_PASS and IONOS_HOST in the environment. The remote
# home root is private (not web-served); it holds both garmin.db and the Garmin
# token store, so treat it as credential storage.

# Run one or more lftp commands against the IONOS SFTP account.
ionos_run() {
  lftp -e "
    set sftp:connect-program 'ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null';
    open sftp://${IONOS_USER}:${IONOS_PASS}@${IONOS_HOST};
    $1
    bye
  "
}

# Bare names of the files in the remote home directory, one per line.
#
# Returns non-zero if the connection or login fails. Callers must treat that as
# fatal: a failed login is not the same as "the file isn't there", and
# conflating the two is what previously let a run start from an empty database.
ionos_list() {
  ionos_run "cls -1;" | tr -d '\r'
}

# True if the named file exists in the remote home directory.
# Expects the listing from ionos_list as $2 so a single connection can answer
# several of these.
ionos_has() {
  printf '%s\n' "$2" | grep -Fxq "$1"
}
