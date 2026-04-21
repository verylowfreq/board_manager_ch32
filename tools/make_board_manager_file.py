from typing import Any, Optional
import urllib.request
import urllib.parse
import json
import pathlib
import hashlib
import os

UPSTREAM_URL = "https://raw.githubusercontent.com/openwch/board_manager_files/main/package_ch32v_index.json"


MY_VERSION = "2.1.4"
MY_VERSION_FULL = f"{MY_VERSION}"
MY_ARCHIVE_URL = f"https://github.com/verylowfreq/arduino_core_ch32_sz/releases/download/{MY_VERSION_FULL}/arduino_core_ch32_sz-{MY_VERSION_FULL}.zip"
MY_ARCHIVE_FILENAME = f"arduino_core_ch32-sz-{MY_VERSION}.zip"


my_core_definition = f"""
        {{
          "name": "CH32V Boards by M.S.",
          "architecture": "ch32v",
          "version": "{MY_VERSION_FULL}",
          "category": "Contributed",
          "url": "{MY_ARCHIVE_URL}",
          "archiveFileName": "",
          "checksum": "",
          "size": "",
          "boards": [
            {{"name": "Suzuno32RV, Suzuno32RV Pro Micro, Suzuduino UNO"}}
          ],
          "toolsDependencies": [
            {{
              "packager": "WCH_sz",
              "name": "riscv-none-embed-gcc",
              "version": "8.2.0"
            }},
            {{
              "packager": "WCH_sz",
              "name": "openocd",
              "version": "1.0.0"
            }},
            {{
              "packager": "WCH_sz",
              "name": "beforeinstall",
              "version": "1.0.0"
            }},
            {{
                "packager": "WCH_sz",
                "name": "wchisp",
                "version": "0.3.0"
            }}
           ]
        }}
"""

tool_wchisp_definition = f"""
        {{
          "name": "wchisp",
          "version": "0.3.0",
          "systems":
          [
            {{
              "host": "x86_64-linux-gnu",
              "url": "https://github.com/ch32-rs/wchisp/releases/download/v0.3.0/wchisp-v0.3.0-linux-x64.tar.gz",
              "archiveFileName": "",
              "checksum": "",
              "size": ""
            }},
            {{
              "host": "i686-mingw32",
              "url": "https://github.com/ch32-rs/wchisp/releases/download/v0.3.0/wchisp-v0.3.0-win-x64.zip",
              "archiveFileName": "",
              "checksum": "",
              "size": ""
            }},
            {{
              "host": "x86_64-apple-darwin",
              "url": "https://github.com/ch32-rs/wchisp/releases/download/v0.3.0/wchisp-v0.3.0-macos-x64.tar.gz",
              "archiveFileName": "",
              "checksum": "",
              "size": ""
            }}
          ]
        }}
"""


def get_base_json(url:str) -> Any:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as res:
        body = res.read().decode('utf-8')
    obj = json.loads(body)
    return obj


def download_file(url:str, filename:str) -> None:
    # if os.path.isfile(filename):
    #     print(f'Skip downloading "{url}"')
    #     return
    print(f'Downloading "{url}"...')
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as res:
        filebody = res.read()
        with open(filename, "wb") as f:
            f.write(filebody)


def get_checksum(filepath:str) -> str:
    m = hashlib.sha256()
    with open(filepath, "rb") as f:
        m.update(f.read())
    return f"SHA-256:{m.hexdigest()}"


def get_filesize(filepath:str) -> int:
    p = pathlib.Path(filepath)
    return p.stat().st_size

def get_filename_from_url(url:str) -> str:
    parsed_url = urllib.parse.urlsplit(url)
    filename = parsed_url.path.split('/')[-1]
    if filename == '':
        # ルートURLの場合
        raise RuntimeError('URL does not contain filename')
    else:
        return filename

def update_fileinfo_from_archive(src:Any) -> None:
    url = src['url']
    filename = get_filename_from_url(url)
    download_file(url, filename)
    filesize = get_filesize(filename)
    checksum = get_checksum(filename).upper()
    src["archiveFileName"] = filename
    src["checksum"] = checksum
    src["size"] = f"{filesize}"


def process_tools(src:Any) -> Any:
    print(f'Process tools...')
    base = src
    for i in range(len(base["systems"])):
        p = base["systems"][i]
        update_fileinfo_from_archive(p)
        base["systems"][i] = p
    print(f'Tools definitions updated.')
    return base


def process_core(src:Any) -> Any:
    print(f'Process core...')
    update_fileinfo_from_archive(src)
    print(f'Core definition updated.')
    return src

def replace_beforeinstall(src:Any) -> Any:
    tools = src["packages"][0]["tools"]
    beforeinstall_systems = [ tool for tool in tools if tool["name"] == "beforeinstall" ][0]["systems"]
    beforeinstall_windows = [ host for host in beforeinstall_systems if host["host"] == "i686-mingw32"][0]
    beforeinstall_windows["url"] = "https://raw.githubusercontent.com/verylowfreq/board_manager_ch32/dev/empty.zip"
    beforeinstall_windows["archiveFileName"] = "empty.zip"
    beforeinstall_windows["checksum"] = "SHA-256:0F8F99A6B5F8F197E9BA5F5150BE28F87D23797EB13328FE8035A81D4E826F33"
    beforeinstall_windows["size"] = "164"

    return src

def replace_board_name(src:Any) -> Any:
    src["packages"][0]["name"] = "WCH_sz"
    return src

def get_existing_platforms(path:str) -> list[Any]:
    if not os.path.isfile(path):
        return []
    with open(path, "r") as f:
        defs = json.load(f)
    return defs["packages"][0].get("platforms", [])

def prepend_platform_with_history(new_platform:Any, old_platforms:list[Any]) -> list[Any]:
    # Deduplicate by (name, architecture, version), keeping newest entry first.
    new_key = (
        new_platform.get("name"),
        new_platform.get("architecture"),
        new_platform.get("version"),
    )
    merged = [new_platform]
    for p in old_platforms:
        old_key = (p.get("name"), p.get("architecture"), p.get("version"))
        if old_key == new_key:
            continue
        merged.append(p)
    return merged

def main() -> None:

    my_json_file = "package_ch32v_index_sz.json"
    upstream_json_file = "upstream_package_ch32v_index.json"
    download_file(UPSTREAM_URL, upstream_json_file)

    with open(upstream_json_file, "r") as f:
        upstream_defs = json.load(f)
    
    coredef = json.loads(my_core_definition)
    coredef = process_core(coredef)
    # print(json.dumps(coredef, indent=4, separators=(',', ': ')))

    upstream_defs['packages'][0]['maintainer'] = 'verylowfreq'
    upstream_defs['packages'][0]['email'] = ''
    upstream_defs['packages'][0]['help'] = {}

    old_platforms = get_existing_platforms(my_json_file)
    upstream_defs['packages'][0]['platforms'] = prepend_platform_with_history(coredef, old_platforms)

    tools = json.loads(tool_wchisp_definition)
    tools = process_tools(tools)

    # print(json.dumps(tools, indent=4, separators=(',', ': ')))

    upstream_defs['packages'][0]['tools'].append(tools)

    mydefs = replace_beforeinstall(upstream_defs)
    mydefs = replace_board_name(mydefs)

    # print(json.dumps(upstream_defs, indent=4, separators=(',', ': ')))

    with open(my_json_file, "w") as f:
        json.dump(mydefs, f, indent=4, separators=(',', ': '))

main()
