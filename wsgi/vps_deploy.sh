#!/bin/bash

access_token=
if [ -z $1 ]; then head=master; else head=$1; fi
repo_url="https://github.com/est/rhcloud/tarball/$head"
url="https://api.github.com/repos/est/rhcloud/tarball/$head"
www_dir="/home/est/sites/rhcloud"

#wget --no-check-certificate -Sq -O- $repo_url | tar -C $www_dir --strip=1 -zmxf -
# rev=`ls -d PREFIX-$repo_name* | awk '{print substr($1,length($1)-39)}'`



rev=$(wget -Sq -O- $url 2> >( 
    grep "Content-Disposition:" | 
    tail -1 | 
    awk 'match($0, /filename=.+\-([a-zA-Z0-9]+)\./, f){ print f[1] }'
    ) > >(
    tar -C $www_dir --strip=1 -zmxf -
    ))

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo `date --rfc-3339=s`,$rev,$SSH_CONNECTION >> $DIR/var/deploy.log