# Automatically generated file. DO NOT MODIFY
#

PRODUCT_SOONG_NAMESPACES += \
    $(LOCAL_PATH)

PRODUCT_PACKAGES += \
    FamilyLinkParentalControls \
    Phonesky \
    libjni_latinimegoogle \
    com.google.android.gmssystem.prodvic

ifeq ($(TARGET_IS_GROUPER),)
PRODUCT_PACKAGES += \
    SetupWizard \
    SpeechServicesByGoogle \
    Velvet \
    talkback
endif

$(call inherit-product, vendor/gapps/common/common-vendor.mk)
