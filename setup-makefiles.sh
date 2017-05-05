#!/bin/bash
#
# Copyright (C) 2016 The CyanogenMod Project
# Copyright (C) 2017 The LineageOS Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

set -e

export GAPPS_COMMON=common
export VENDOR=gapps

# Load extract_utils and do some sanity checks
MY_DIR="${BASH_SOURCE%/*}"
if [[ ! -d "$MY_DIR" ]]; then MY_DIR="$PWD"; fi

CM_ROOT="$MY_DIR"/../..

HELPER="$CM_ROOT"/vendor/cm/build/tools/extract_utils.sh
if [ ! -f "$HELPER" ]; then
    echo "Unable to find helper script at $HELPER"
    exit 1
fi
. "$HELPER"

while [ "$1" != "" ]; do
    case $1 in
        -t | --target )         shift
                                export TARGET=$1
    esac
    shift
done

if [ -z "$TARGET" ]; then
    echo "Warning, target for extraction not specified, defaulting to arm"
    TARGET=arm
fi

# Initialize the helper for common gapps
setup_vendor "$GAPPS_COMMON" "$VENDOR" "$CM_ROOT" true

# Copyright headers
write_headers "arm arm64 x86"

# Common gapps
write_makefiles "$MY_DIR"/proprietary-files-common.txt

# We are done with common
write_footers

# Reinitialize the helper for target gapps
setup_vendor "$TARGET" "$VENDOR" "$CM_ROOT" true

# Copyright headers and guards
write_headers "$TARGET"

write_makefiles "$MY_DIR"/proprietary-files-$TARGET.txt

printf '\n%s\n' "\$(call inherit-product, vendor/gapps/common/common-vendor.mk)" >> "$PRODUCTMK"

# We are done with target
write_footers

find "$MY_DIR" -type f -name Android.mk -exec sed -i 's/TARGET_DEVICE/TARGET_ARCH/g' {} \;
