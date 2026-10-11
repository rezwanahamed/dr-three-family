#!/usr/bin/env python3
"""Optional refresh tool. Next is used only to regenerate markup, never at runtime."""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, default=ROOT.parent / 'main_website/dental_family')
args = parser.parse_args()
source = args.source.resolve()
if not (source / 'node_modules/next').exists():
    parser.error('Install the original website dependencies first.')

with tempfile.TemporaryDirectory(prefix='dental-django-export-') as temporary:
    stage = Path(temporary)
    for name in ['app', 'public']:
        shutil.copytree(source / name, stage / name)
    for name in ['package.json', 'tsconfig.json', 'postcss.config.mjs', 'next-env.d.ts']:
        if (source / name).exists():
            shutil.copy2(source / name, stage / name)
    (stage / 'node_modules').symlink_to(source / 'node_modules', target_is_directory=True)
    (stage / 'next.config.mjs').write_text('export default {output:"export",trailingSlash:true,images:{unoptimized:true},experimental:{cpus:2}};\n')
    for name in ['robots.ts', 'sitemap.ts']:
        path = stage / 'app' / name
        text = path.read_text()
        if 'export const dynamic' not in text:
            path.write_text('export const dynamic = "force-static";\n' + text)
    path = stage / 'app/motion-ui.tsx'
    text = path.read_text().replace('<motion.section\n', '<motion.section\n      data-reveal=""\n')
    text = text.replace('<MotionNextLink\n', '<MotionNextLink\n      data-lift=""\n')
    path.write_text(text)
    path = stage / 'app/hero.tsx'
    path.write_text(path.read_text().replace('initial: false as const,', '"data-hero-enter": delay,\n    initial: false as const,'))
    path = stage / 'app/migration-error/page.tsx'
    path.parent.mkdir()
    path.write_text('import { RecoveryScreen } from "../recovery-screen";\nexport const metadata = {title: "Something went wrong | Dr. Teeth Family Dental", robots: {index:false,follow:false}};\nexport default function Page(){return <RecoveryScreen kind="error" />;}\n')
    subprocess.run(['node', 'node_modules/next/dist/bin/next', 'build', '--webpack'], cwd=stage, check=True)
    subprocess.run([sys.executable, str(ROOT / 'tools/convert.py'), str(stage / 'out'), '--source', str(source)], check=True)
