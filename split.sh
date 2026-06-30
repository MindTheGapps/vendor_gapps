#!/bin/bash
find {arm,arm64,common} -size +99M -exec split -b 99M --numeric-suffixes {} {}. \; -delete
