#!/usr/bin/env python3
"""Verify Firefox user.js has all required privacy prefs.

Usage:
    python3 verify-firefox-privacy-prefs.py [PROFILE_DIR]

If PROFILE_DIR is omitted, searches ~/.mozilla/firefox/ for the default-release
profile automatically.
"""

import sys, os, glob

REQUIRED_PREFS = [
    # Telemetry / Normandy
    ('datareporting.healthreport.uploadEnabled',          'false'),
    ('datareporting.policy.dataSubmissionEnabled',        'false'),
    ('app.shield.optoutstudies.enabled',                  'false'),
    ('app.normandy.enabled',                              'false'),
    ('browser.crashReports.unsubmittedCheck.autoSubmit2', 'false'),
    # WebRTC
    ('media.peerconnection.enabled',                      'false'),
    # Fingerprinting
    ('privacy.resistFingerprinting',                      'true'),
    ('privacy.resistFingerprinting.letterboxing',         'true'),
    # userChrome
    ('toolkit.legacyUserProfileCustomizations.stylesheets', 'true'),
    # Prefetch
    ('network.prefetch-next',                             'false'),
    ('network.dns.disablePrefetch',                       'true'),
]

NORMANDY_DRIFT_PREFS = [
    'normandy.user_id',
    'datareporting.dau.cachedUsageProfileID',
    'datareporting.policy.dataSubmissionPolicyAcceptedVersion',
]


def find_profile():
    base = os.path.expanduser('~/.mozilla/firefox')
    # Prefer default-release
    for d in glob.glob(f'{base}/*.default-release'):
        if os.path.isfile(f'{d}/prefs.js'):
            return d
    # Fallback: any dir with prefs.js
    for d in glob.glob(f'{base}/*'):
        if os.path.isfile(f'{d}/prefs.js'):
            return d
    return None


def main():
    if len(sys.argv) > 1:
        profile = sys.argv[1]
    else:
        profile = find_profile()

    if not profile:
        print('ERROR: could not find Firefox profile dir')
        sys.exit(2)

    userjs_path  = os.path.join(profile, 'user.js')
    prefsjs_path = os.path.join(profile, 'prefs.js')
    chrome_path  = os.path.join(profile, 'chrome', 'userChrome.css')

    print(f'Profile: {profile}')
    print()

    ok = []; fail = []; warn = []

    # --- user.js checks ---
    if not os.path.exists(userjs_path):
        print('FAIL: user.js not found')
        sys.exit(1)

    with open(userjs_path) as f:
        js = f.read()

    for pref, val in REQUIRED_PREFS:
        needle = f'user_pref("{pref}", {val})'
        if needle in js:
            ok.append(f'user.js  {pref} = {val}')
        else:
            fail.append(f'user.js  MISSING user_pref("{pref}", {val})')

    # --- prefs.js drift check (Normandy / telemetry still registered?) ---
    if os.path.exists(prefsjs_path):
        with open(prefsjs_path) as f:
            prefs = f.read()
        for drift_key in NORMANDY_DRIFT_PREFS:
            if drift_key in prefs:
                warn.append(f'prefs.js drift: "{drift_key}" still present '
                            f'(restart Firefox to let user.js override)')

    # --- userChrome.css check ---
    if os.path.exists(chrome_path):
        with open(chrome_path) as f:
            css = f.read()
        if '.letterboxing .browserContainer' in css and '!important' in css:
            ok.append('userChrome.css  letterboxing color override present')
        else:
            warn.append('userChrome.css exists but letterboxing override may be incomplete')
    else:
        warn.append('userChrome.css not found — letterboxing bars will be grey')

    # --- print results ---
    for x in ok:   print(f'  OK   {x}')
    for x in warn: print(f'  WARN {x}')
    for x in fail: print(f'  FAIL {x}')

    print()
    if fail:
        print(f'FAILED: {len(fail)} missing pref(s) in user.js')
        sys.exit(1)
    else:
        msg = f'PASSED: {len(ok)} checks'
        if warn:
            msg += f', {len(warn)} warning(s)'
        print(msg)


if __name__ == '__main__':
    main()
