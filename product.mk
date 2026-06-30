ifeq ($(WITH_GMS),true)
    ifeq ($(TARGET_ARCH),arm64)
        $(call inherit-product-if-exists, vendor/gapps/arm64/arm64-vendor.mk)
    else ifeq ($(TARGET_ARCH),arm)
        $(call inherit-product-if-exists, vendor/gapps/arm/arm-vendor.mk)
    else ifeq ($(TARGET_ARCH),x86_64)
        $(call inherit-product-if-exists, vendor/gapps/x86_64/x86_64-vendor.mk)
    endif
endif
