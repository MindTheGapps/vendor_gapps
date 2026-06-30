# Automatically generated file. DO NOT MODIFY
#

PRODUCT_SOONG_NAMESPACES += \
    $(LOCAL_PATH)

PRODUCT_PACKAGES += \
    GmsCore \
    Phonesky \
    libjni_latinimegoogle

ifeq ($(TARGET_IS_GROUPER),)
PRODUCT_PACKAGES += \
    SetupWizard \
    SpeechServicesByGoogle \
    Velvet \
    talkback
endif

$(call inherit-product, vendor/gapps/common/common-vendor.mk)
