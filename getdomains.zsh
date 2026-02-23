#!/bin/zsh
#
# This script can, as of 2022-09, get the list of the top 1000 web domains (by some arbitrary criteria) from dataforseo.com.
# The list is useful for e.g. Internet uplink monitoring (at any given time, a large percentage of these webservers should be reachable).
#
# It checks whether /var/lib/netcheck/domains exists and is "fresh" before fetching a new list and saving it there.

CONFIG=/etc/default/${0:t}
OUTFILE=${OUTFILE:-/var/lib/netcheck/domains}
MAXAGE=2592000	# seconds -- default 1 month
RUNASUSER=nobody

[[ -r $CONFIG ]] && . $CONFIG

zmodload zsh/datetime

if [[ $OUTFILE = $(find $OUTFILE -newermt @$[EPOCHSECONDS-MAXAGE] 2>/dev/null) ]]; then
	# File is fresh
	exit 0
else

	mkdir -p ${OUTFILE:h} || exit 111
	chown $RUNASUSER ${OUTFILE:h} $OUTFILE(N)

	USERNAME=$RUNASUSER

	[[ -v TMPDIR ]] && { [[ -w $TMPDIR ]] || unset TMPDIR }
	tmpfile=$(mktemp) || exit 111

	curl https://dataforseo.com/wp-admin/admin-ajax.php \
		-X POST \
		-H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:104.0) Gecko/20100101 Firefox/104.0' \
		-H 'Accept: application/json, text/javascript, */*; q=0.01' \
		-H 'Accept-Language: en-GB,en-US,en' \
		-H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' \
		-H 'X-Requested-With: XMLHttpRequest' \
		-H 'Origin: https://dataforseo.com' \
		-H 'Alt-Used: dataforseo.com' \
		-H 'Referer: https://dataforseo.com/top-1000-websites' \
		-H 'Sec-Fetch-Dest: empty' \
		-H 'Sec-Fetch-Mode: cors' \
		-H 'Sec-Fetch-Site: same-origin' \
		-H 'Sec-GPC: 1' \
		--data-raw 'action=dfs_ranked_domains&location=2348' \
		--silent \
		| sed 's/},{/\n/g' \
		| cut -d'"' -f6 \
		>$tmpfile

	curlret=$?
	if [[ $curlret = 0 ]] && [[ $(wc -l < $tmpfile) = 1000 ]]; then
		cat $tmpfile >$OUTFILE
		rm $tmpfile
		exit 0
	else
		echo "Error fetching top 1000 domains. Curl returned with exit status $curlret. Evidence preserved in $tmpfile." >&2
		exit 1
	fi
fi
