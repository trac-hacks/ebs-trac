#! /bin/sh -e
#
# Add a new entry to ../dat/act.txt with current start time.
#


usage="$0 <taskid> [<username>]"

# Get task id and optionally username from command line args.
[ "x$1" = x ] && echo $usage && exit 1
taskid=$1
user=$(whoami)
if [ "x$2" != "x" ]; then user=$2; fi

# Make sure we can find file holding actual data.
fn=./dat/act.txt
if [ ! -f $fn ]; then 
	echo "ERROR: can't open $fn"
	exit 1
fi

dt=$(date +%F)
tm=$(date +%T)

cat >> $fn << EOF
$taskid	$user	$dt	$tm
EOF
