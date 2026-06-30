# Automatically generated file. DO NOT MODIFY
#

PRODUCT_SOONG_NAMESPACES += \
    $(LOCAL_PATH)

PRODUCT_PACKAGES += \
    Phonesky \
    libjni_latinimegoogle \
    com.google.android.gmssystem.prodvic

ifeq ($(TARGET_IS_GROUPER),)
PRODUCT_PACKAGES += \
    MarkupGoogle_v2 \
    SetupWizard \
    SpeechServicesByGoogle \
    Velvet \
    talkback
endif

ifneq ($(filter %tangorpro,$(TARGET_PRODUCT)),)
PRODUCT_PACKAGES += \
    VelvetTitan
endif

$(call inherit-product, vendor/gapps/common/common-vendor.mk)
