from typing import Any, Optional
import urllib.request
import urllib.parse
import json
import pathlib
import hashlib
import os

UPSTREAM_URL = "https://raw.githubusercontent.com/openwch/board_manager_files/main/package_ch32v_index.json"


MY_VERSION = "1.0.4"
MY_VERSION_APPENDIX = "+sz4"
MY_VERSION_FULL = f"{MY_VERSION}{MY_VERSION_APPENDIX}"
MY_ARCHIVE_URL = "https://github.com/verylowfreq/arduino_core_ch32_sz/releases/download/1.0.4-sz4/arduino_core_ch32_sz-1.0.4+sz4.zip"
MY_ARCHIVE_FILENAME = f"arduino_core_ch32-sz-{MY_VERSION}{MY_VERSION_APPENDIX}.zip"


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
            {{"name": "CH32V Boards by M.S."}}
          ],
          "toolsDependencies": [
            {{
              "packager": "WCH",
              "name": "riscv-none-embed-gcc",
              "version": "8.2.0"
            }},
            {{
              "packager": "WCH",
              "name": "openocd",
              "version": "1.0.0"
            }},
            {{
              "packager": "WCH",
              "name": "beforeinstall",
              "version": "1.0.0"
            }},
            {{
                "packager": "WCH",
                "name": "wchisp",
                "version": "0.2.3+sz1"
            }}
           ]
        }}
"""

tool_wchisp_definition = f"""
        {{
          "name": "wchisp",
          "version": "0.2.3+sz1",
          "systems":
          [
            {{
              "host": "x86_64-linux-gnu",
              "url": "https://github.com/ch32-rs/wchisp/releases/download/v0.2.3/wchisp-v0.2.3-linux-x64.tar.gz",
              "archiveFileName": "",
              "checksum": "",
              "size": ""
            }},
            {{
              "host": "i686-mingw32",
              "url": "https://github.com/ch32-rs/wchisp/releases/download/v0.2.3/wchisp-v0.2.3-win-x64.zip",
              "archiveFileName": "",
              "checksum": "",
              "size": ""
            }},
            {{
              "host": "x86_64-apple-darwin",
              "url": "https://github.com/ch32-rs/wchisp/releases/download/v0.2.3/wchisp-v0.2.3-macos-x64.zip",
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

    upstream_defs['packages'][0]['platforms'].clear()
    upstream_defs['packages'][0]['platforms'].append(coredef)

    tools = json.loads(tool_wchisp_definition)
    tools = process_tools(tools)

    # print(json.dumps(tools, indent=4, separators=(',', ': ')))

    upstream_defs['packages'][0]['tools'].append(tools)

    # print(json.dumps(upstream_defs, indent=4, separators=(',', ': ')))

    mydefs = upstream_defs

    with open(my_json_file, "w") as f:
        json.dump(mydefs, f, indent=4, separators=(',', ': '))

main()
