"""Verify the first N67 port increment; requires CHAOS_FW and FENGARI_PATH."""
from pathlib import Path
import json, os, subprocess, sys

ROOT = Path(__file__).resolve().parents[1]
checks = [
    [sys.executable, str(ROOT/'tools/test_native_notice.py')],
    [sys.executable, str(ROOT/'tools/test_gh225_route.py')],
    ['node', str(ROOT/'tools/check_data_version.cjs')],
    [sys.executable, str(ROOT/'tools/test_registrar_detach.py')],
    [sys.executable, str(ROOT/'tools/test_delivery_compat.py')],
    [sys.executable, str(ROOT/'tools/test_entry_preflight.py')],
    ['node', str(ROOT/'tools/check_entry_preflight.cjs')],
    [sys.executable, str(ROOT/'tools/test_install_health.py')],
    ['node', str(ROOT/'tools/check_install_health.cjs')],
    [sys.executable, str(ROOT/'tools/test_shake.py')],
    [sys.executable, str(ROOT/'tools/test_backdrop_render.py')],
    [sys.executable, str(ROOT/'tools/check_bootstrap190.py')],
    [sys.executable, str(ROOT/'tools/check_photo15.py')],
    [sys.executable, str(ROOT/'tools/check_files190.py')],
    [sys.executable, str(ROOT/'tools/test_port_pages.py')],
    [sys.executable, str(ROOT/'tools/test_datetime.py')],
    [sys.executable, str(ROOT/'tools/test_native_ui.py')],
    [sys.executable, str(ROOT/'tools/test_notifications.py')],
    [sys.executable, str(ROOT/'tools/test_system_custom.py')],
    [sys.executable, str(ROOT/'tools/test_app_manager.py')],
    [sys.executable, str(ROOT/'tools/test_app_details.py')],
    [sys.executable, str(ROOT/'tools/test_native_entries.py')],
    [sys.executable, str(ROOT/'tools/test_background.py')],
    [sys.executable, str(ROOT/'tools/test_swipe_vibration.py')],
    [sys.executable, str(ROOT/'tools/test_vibration_errors.py')],
    [sys.executable, str(ROOT/'tools/test_diagnostics.py')],
    [sys.executable, str(ROOT/'tools/test_desktop_scale.py')],
    [sys.executable, str(ROOT/'tools/test_beautify_restore.py')],
    ['node', str(ROOT/'tools/check_n67_runtime.cjs')],
    ['node', str(ROOT/'tools/check_installer_actions.cjs')],
]
profile=json.loads((ROOT/'n67/manifest.json').read_text('utf8')).get('profile','standard')
if profile=='settings-egg':
    checks=[c for c in checks if Path(c[1]).name not in ('test_native_entries.py','test_app_manager.py','check_installer_actions.cjs')]
checks.append([sys.executable,str(ROOT/'tools/test_settings_egg.py')])
checks.append([sys.executable,str(ROOT/'tools/test_scroll_performance.py')])
results = []
for command in checks:
    p = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf8')
    print(p.stdout, end='')
    if p.stderr: print(p.stderr, file=sys.stderr, end='')
    results.append({'check': Path(command[1]).name, 'exit_code': p.returncode,
                    'stdout': p.stdout, 'stderr': p.stderr})
    if p.returncode:
        raise SystemExit(p.returncode)
(ROOT/'n67/generated/port-validation.json').write_text(
    json.dumps({'hardware_tested': False, 'profile':profile, 'checks': results}, ensure_ascii=False, indent=2),
    encoding='utf8')
print('PASS all desktop checks; hardware APIs and GUI are mocked in the ARM tests.')
