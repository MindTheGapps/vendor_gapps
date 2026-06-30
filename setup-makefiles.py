#!/usr/bin/env python3
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
import glob
import textwrap
import typing


@dataclass
class GappsTarget:
    name: str
    soong_imports: list[str]
    additional_namespaces: list[str]
    additional_packages: list[str]
    additional_makefiles_to_inherit: list[str]


class SoongModule:
    def __init__(self):
        self.soong_module = type(self).__name__

    @staticmethod
    def _value_to_str(value: typing.Any) -> str:
        match value:
            case bool():
                return ["false", "true"][value]
            case dict():
                ret = "{\n"

                for key, value in value.items():
                    ret += f"{indent(SoongModule._prop_to_str(key, value))}\n"

                ret += "}"

                return ret
            case list():
                return f'[{", ".join([SoongModule._value_to_str(x) for x in value])}]'
            case str():
                return f'"{value}"'
            case default:
                assert False, f"Unhandled value type: {type(value)}"

    @staticmethod
    def _prop_to_str(key: str, value: typing.Any) -> str:
        return f"{key}: {SoongModule._value_to_str(value)},"

    def _to_blueprint(self, props: dict) -> str:
        ret = f"{self.soong_module} {{\n"

        for key, value in props.items():
            ret += f"{indent(SoongModule._prop_to_str(key, value))}\n"

        ret += "}"

        return ret


class SoongPrebuilt(SoongModule):
    def __init__(self, target_name: str, install_path: str, flags: dict):
        SoongModule.__init__(self)

        self.name = Path(install_path).stem
        self.install_path = install_path
        self.src = f"proprietary/{install_path}"
        self.filename = self.src.split("/")[-1]
        self.flags = flags

        if parts := sorted(glob.glob(f"{self.src}.*", root_dir=target_name)):
            self.genrule = genrule(self.filename, parts).to_blueprint()
            self.src = f":{self.filename}-genrule"

    def _has_flag(self, key: str) -> bool:
        return key in self.flags

    def _flag(self, key: str) -> str | None:
        return self.flags.get(key, None)

    def _to_blueprint(self, props: dict) -> str:
        partition, _ = self.install_path.split("/", maxsplit=1)

        match partition:
            case "system":
                pass
            case "product":
                props["product_specific"] = True
            case "system_ext":
                props["system_ext_specific"] = True
            case _:
                assert False, f"Unhandled partition: {partition}"

        ret = super()._to_blueprint(props)

        if hasattr(self, "genrule"):
            ret = f"{self.genrule}\n\n{ret}"

        return ret


class android_app_import(SoongPrebuilt):
    def to_blueprint(self) -> str:
        props = {
            "name": self.name,
            "owner": "gapps",
            "apk": self.src,
            "overrides": [self._flag("OVERRIDES")],
            "preprocessed": True,
            "presigned": True,
            "dex_preopt": {
                "enabled": False,
            },
            "privileged": True,
        }

        _, apk_dst, _ = self.install_path.split("/", maxsplit=2)

        if apk_dst != "priv-app":
            del props["privileged"]

        if not self._has_flag("OVERRIDES"):
            del props["overrides"]

        if not self._has_flag("PRESIGNED"):
            del props["presigned"]

        return self._to_blueprint(props)


class cc_prebuilt_library_shared(SoongPrebuilt):
    def to_blueprint(self) -> str:
        props = {
            "name": self.name,
            "srcs": [self.src],
            "prefer": True,
        }

        return self._to_blueprint(props)


class dex_import(SoongPrebuilt):
    def to_blueprint(self) -> str:
        props = {
            "name": self.name,
            "owner": "gapps",
            "jars": [self.src],
        }

        return self._to_blueprint(props)


class genrule(SoongModule):
    def __init__(self, filename: str, parts: list[str]):
        super().__init__()

        self.filename = filename
        self.parts = parts

    def to_blueprint(self) -> str:
        props = {
            "name": f"{self.filename}-genrule",
            "out": [self.filename],
            "cmd": "cat $(in) > $(out)",
            "srcs": self.parts,
        }

        return self._to_blueprint(props)


class prebuilt_apex(SoongPrebuilt):
    def to_blueprint(self) -> str:
        props = {
            "name": self.name,
            "owner": "gapps",
            "src": self.src,
            "filename": self.filename,
            "apps": [self._flag("APPS")],
        }

        if not self._has_flag("APPS"):
            del props["apps"]

        return self._to_blueprint(props)


class prebuilt_etc(SoongPrebuilt):
    def __init__(self, target_name: str, install_path: str, flags: dict):
        super().__init__(target_name, install_path, flags)

        self.name += Path(self.install_path).suffix

    def to_blueprint(self) -> str:
        props = {
            "name": self.name,
            "src": self.src,
            "relative_install_path": "/".join(self.install_path.split("/")[2:-1]),
            "filename_from_src": True,
        }

        return self._to_blueprint(props)


class soong_namespace(SoongModule):
    def __init__(self, imports: list[str]):
        super().__init__()

        self.imports = imports

    def to_blueprint(self) -> str:
        props = {
            "imports": self.imports,
        }

        if not self.imports:
            del props["imports"]

        return self._to_blueprint(props)


def indent(text: str) -> str:
    return textwrap.indent(text, " " * 4)


def parse_proprietary_file(target_name: str, line: str) -> SoongPrebuilt:
    # Format: ORIG_PATH:INSTALL_PATH;FLAGS|SHA1

    if "|" in line:
        line, file_hash = line.split("|")
    else:
        file_hash = None

    if ";" in line:
        line, flags_str = line.split(";", maxsplit=1)
        flags = {}
        for flag in flags_str.split(";"):
            if "=" in flag:
                key, value = flag.split("=", maxsplit=1)
            else:
                key = flag
                value = None
            flags[key] = value
    else:
        flags = {}

    if ":" in line:
        line, install_path = line.split(":")
    else:
        install_path = line

    for pattern, blob_type in {
        "*.apex": prebuilt_apex,
        "*.apk": android_app_import,
        "*.jar": dex_import,
        "*.so": cc_prebuilt_library_shared,
        "*/etc/*.*": prebuilt_etc,
    }.items():
        if fnmatch(install_path, pattern):
            return blob_type(target_name, install_path, flags)
    else:
        assert False, f"Unhandled install path: {install_path}"


def parse_proprietary_files(target_name: str, path: str) -> list:
    packages = []

    if Path(path).is_file():
        for line in open(path).readlines():
            line = line.strip()

            if not line:
                continue

            if package := parse_proprietary_file(target_name, line):
                packages.append(package)

    return sorted(packages, key=lambda x: (x.soong_module, x.name))


def generate(targets: list[GappsTarget]) -> None:
    for target in targets:
        packages = parse_proprietary_files(
            target.name, f"proprietary-files-{target.name}.txt"
        )
        packages_nongrouper = parse_proprietary_files(
            target.name, f"proprietary-files-{target.name}-nongrouper.txt"
        )
        packages_tangorpro = parse_proprietary_files(
            target.name, f"proprietary-files-{target.name}-tangorpro.txt"
        )
        packages_all = sorted(
            packages + packages_nongrouper + packages_tangorpro,
            key=lambda x: (x.soong_module, x.name),
        )

        with open(f"{target.name}/Android.bp", "+wt") as f:
            f.write("// Automatically generated file. DO NOT MODIFY\n")
            f.write("\n")

            f.write(soong_namespace(target.soong_imports).to_blueprint())
            f.write("\n")

            for package in packages_all:
                f.write("\n")
                f.write(package.to_blueprint())
                f.write("\n")

        with open(f"{target.name}/BoardConfigVendor.mk", "+wt") as f:
            f.write("# Automatically generated file. DO NOT MODIFY\n")
            f.write("#\n")

        with open(f"{target.name}/{target.name}-vendor.mk", "+wt") as f:
            f.write("# Automatically generated file. DO NOT MODIFY\n")
            f.write("#\n")

            def write_list(var: str, items: list[str]):
                f.write(f"{var} += \\\n")
                f.write(" \\\n".join([indent(x) for x in items]))
                f.write("\n")

            f.write("\n")
            write_list("PRODUCT_SOONG_NAMESPACES", [f"$(LOCAL_PATH)"])

            if packages:
                f.write("\n")
                write_list("PRODUCT_PACKAGES", [x.name for x in packages])

            if packages_nongrouper:
                f.write("\n")
                f.write("ifeq ($(TARGET_IS_GROUPER),)\n")
                write_list("PRODUCT_PACKAGES", [x.name for x in packages_nongrouper])
                f.write("endif\n")

            if packages_tangorpro:
                f.write("\n")
                f.write("ifneq ($(filter %tangorpro,$(TARGET_PRODUCT)),)\n")
                write_list("PRODUCT_PACKAGES", [x.name for x in packages_tangorpro])
                f.write("endif\n")

            if target.additional_namespaces:
                f.write("\n")
                write_list("PRODUCT_SOONG_NAMESPACES", target.additional_namespaces)

            if target.additional_packages:
                f.write("\n")
                write_list("PRODUCT_PACKAGES", target.additional_packages)

            for path in target.additional_makefiles_to_inherit:
                f.write("\n")
                f.write(f"$(call inherit-product, {path})\n")


if __name__ == "__main__":
    generate(
        [
            GappsTarget(
                name="common",
                soong_imports=[],
                additional_namespaces=["vendor/gapps/overlay"],
                additional_packages=sorted(
                    [x.name for x in Path("overlay").glob("*Overlay")]
                ),
                additional_makefiles_to_inherit=[],
            ),
            GappsTarget(
                name="arm",
                soong_imports=["vendor/gapps/common"],
                additional_namespaces=[],
                additional_packages=[],
                additional_makefiles_to_inherit=[
                    "vendor/gapps/common/common-vendor.mk",
                ],
            ),
            GappsTarget(
                name="arm64",
                soong_imports=["vendor/gapps/common"],
                additional_namespaces=[],
                additional_packages=[],
                additional_makefiles_to_inherit=[
                    "vendor/gapps/common/common-vendor.mk",
                ],
            ),
        ]
    )
