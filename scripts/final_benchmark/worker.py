"""Offline subprocess worker; no credentials supplied in its environment."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'skills/multilingual-visual-benchmark/scripts'))


def main():
    spec_path, locale_path, output = map(Path, sys.argv[1:4])
    output.parent.mkdir(parents=True, exist_ok=True)
    os.environ['MPLCONFIGDIR'] = str(output.parent / '.matplotlib_cache')
    import multilingual_drawing as drawing
    from scripts.final_benchmark import render_runtime as runtime
    runtime.put, runtime.wrap, runtime.mask = drawing.put, drawing.wrap, drawing.mask
    spec = json.loads(spec_path.read_text())
    locale = json.loads(locale_path.read_text())
    labels = locale.get('labels', locale)
    if spec['kind'] == 'chart':
        runtime.validate_code(spec['python_code'])
        namespace = {k: v for k, v in vars(runtime).items() if not k.startswith('_')}
        exec(compile(spec['python_code'], '<validated_chart_adapter>', 'exec'), namespace)
        image, boxes = namespace['render'](spec['data'], labels)
    else:
        spec['data']['layout'] = spec['data'].get('layout') or runtime.table_layout(spec['data'], [labels])
        image, boxes = runtime.render_table(spec['data'], labels)
    if image.width * image.height > 50000000:
        raise ValueError('image_too_large')
    image.save(output, optimize=True)
    report = {'width': image.width, 'height': image.height, 'boxes': boxes,
              'fonts_used': sorted(drawing.USED_FONTS),
              'missing_glyphs': sorted(set(drawing.MISSING_GLYPHS)),
              'all_text_inside_canvas': all(b['inside_canvas'] for b in boxes),
              'all_text_inside_cells': all(b.get('inside_cell', True) for b in boxes)}
    output.with_suffix('.layout.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
