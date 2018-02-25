#!/bin/bash
#
# Copyright (C) 2016 The CyanogenMod Project
# Copyright (C) 2017-2018 The LineageOS Project
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

export INITIAL_COPYRIGHT_YEAR=2017

export GAPPS_COMMON=common
export VENDOR=gapps

# Load extract_utils and do some sanity checks
MY_DIR="${BASH_SOURCE%/*}"
if [[ ! -d "$MY_DIR" ]]; then MY_DIR="$PWD"; fi

LINEAGE_ROOT="$MY_DIR"/../..

HELPER="$LINEAGE_ROOT"/vendor/lineage/build/tools/extract_utils.sh
if [ ! -f "$HELPER" ]; then
    echo "Unable to find helper script at $HELPER"
    exit 1
fi
. "$HELPER"

# Initialize the helper for common gapps
setup_vendor "$GAPPS_COMMON" "$VENDOR" "$LINEAGE_ROOT" true

# Copyright headers
write_headers "arm arm64 x86"

# Common gapps
write_makefiles "$MY_DIR"/proprietary-files-common.txt

sed -i 's/TARGET_DEVICE/TARGET_ARCH/g' "$ANDROIDMK"

# extract_utils struggles with extracting to a different dest
sed -i 's/\(LOCAL_MODULE := \)LeanbackLauncher/\1LeanbackLauncherO/g' "$ANDROIDMK"
sed -i 's/\(LeanbackLauncher\) \\/\1O \\/g' "$PRODUCTMK"

# Make LeanbackLauncherO override LeanbackLauncher
sed -i 's/\(LeanbackLauncher.apk\)/\1\nLOCAL_OVERRIDES_PACKAGES := LeanbackLauncher/' "$ANDROIDMK"

# We are done with common
write_footers

for TARGET in arm arm64 x86; do

# Reinitialize the helper for target gapps
setup_vendor "$TARGET" "$VENDOR" "$LINEAGE_ROOT" true

# Copyright headers and guards
write_headers "$TARGET"

write_makefiles "$MY_DIR"/proprietary-files-$TARGET.txt

printf '\n%s\n' "\$(call inherit-product, vendor/gapps/common/common-vendor.mk)" >> "$PRODUCTMK"

sed -i 's/TARGET_DEVICE/TARGET_ARCH/g' "$ANDROIDMK"

# We are done with target
write_footers

done
