"""
translate_notebooks.py

Usage:
  python translate_notebooks.py --src notebooks --dest notebooks_es --lang es

Notes:
- The script translates markdown cells only and leaves code cells unchanged.
- It tries `deep_translator` first, then `googletrans` as a fallback.
- If neither package is installed, it will print install instructions.
"""

import argparse
import io
import json
import os
import sys
from typing import List


def find_notebooks(src_dir: str) -> List[str]:
    out = []
    for root, _, files in os.walk(src_dir):
        for f in files:
            if f.endswith('.ipynb'):
                out.append(os.path.join(root, f))
    return sorted(out)


def translate_with_deep_translator(text: str, target: str) -> str:
    from deep_translator import GoogleTranslator
    return GoogleTranslator(source='auto', target=target).translate(text)


def translate_with_googletrans(text: str, target: str) -> str:
    from googletrans import Translator
    t = Translator()
    return t.translate(text, dest=target).text


def get_translator():
    try:
        import deep_translator  # type: ignore
        return 'deep_translator'
    except Exception:
        try:
            import googletrans  # type: ignore
            return 'googletrans'
        except Exception:
            return None


def translate_text(text: str, target: str) -> str:
    provider = get_translator()
    if provider == 'deep_translator':
        return translate_with_deep_translator(text, target)
    if provider == 'googletrans':
        return translate_with_googletrans(text, target)
    raise ModuleNotFoundError('No translation provider installed')


def translate_notebook(path: str, dest_path: str, lang: str) -> None:
    with io.open(path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    cells = nb.get('cells', [])
    changed = False
    for cell in cells:
        ctype = cell.get('cell_type')
        # treat as markdown if cell_type == 'markdown'
        if ctype == 'markdown':
            src = cell.get('source', [])
            if isinstance(src, list):
                text = ''.join(src)
            else:
                text = str(src)
            if text.strip() == '':
                continue
            try:
                translated = translate_text(text, lang)
            except ModuleNotFoundError as e:
                raise
            # convert back to list of lines with endings preserved
            lines = translated.splitlines(keepends=True)
            # ensure each line ends with a newline except maybe last
            cell['source'] = lines
            changed = True

    # ensure dest dir exists
    os.makedirs(os.path.dirname(dest_path) or '.', exist_ok=True)
    with io.open(dest_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)

    return changed


def main():
    parser = argparse.ArgumentParser(description='Translate notebook markdown to another language')
    parser.add_argument('--src', default='notebooks', help='Source notebooks directory')
    parser.add_argument('--dest', default='notebooks_es', help='Destination directory for translated notebooks')
    parser.add_argument('--lang', default='es', help='Target language code (e.g., es)')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing files in dest')
    args = parser.parse_args()

    provider = get_translator()
    if provider is None:
        print('\nNo translation package detected. Install one of:')
        print('\n  pip install deep-translator')
        print('  or')
        print("  pip install googletrans==4.0.0-rc1\n")
        sys.exit(2)

    notebooks = find_notebooks(args.src)
    if not notebooks:
        print('No notebooks found under', args.src)
        sys.exit(1)

    print(f'Found {len(notebooks)} notebooks. Using provider: {provider}')
    for nb in notebooks:
        rel = os.path.relpath(nb, args.src)
        dest_nb = os.path.join(args.dest, rel)
        if os.path.exists(dest_nb) and not args.overwrite:
            print('Skipping (exists):', dest_nb)
            continue
        try:
            os.makedirs(os.path.dirname(dest_nb) or '.', exist_ok=True)
            translate_notebook(nb, dest_nb, args.lang)
            print('Translated:', rel)
        except ModuleNotFoundError:
            print('Translation provider missing at runtime. Aborting.')
            sys.exit(2)
        except Exception as ex:
            print('Error translating', rel, '-', ex)

    print('\nDone. Translated notebooks are in', args.dest)

if __name__ == '__main__':
    main()
