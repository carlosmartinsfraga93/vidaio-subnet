"""
Check if VMAF models are available
"""

import os

print("=" * 80)
print("VMAF Model Availability Check")
print("=" * 80)

# Check common vmafneg model locations
vmafneg_paths = [
    "/usr/local/share/vmaf/model/vmaf_v0.6.1neg.json",
    "/usr/share/vmaf/model/vmaf_v0.6.1neg.json",
    "./models/vmaf/vmaf_v0.6.1neg.json",
    "services/compress/models/vmaf/vmaf_v0.6.1neg.json"
]

print("\n📋 Checking VMAFNEG model locations:")
vmafneg_found = None
for path in vmafneg_paths:
    exists = os.path.exists(path)
    status = "✅" if exists else "❌"
    print(f"   {status} {path}")
    if exists and not vmafneg_found:
        vmafneg_found = path

# Check default VMAF model locations
default_vmaf_paths = [
    "/usr/local/share/vmaf/model/vmaf_v0.6.1.json",
    "/usr/share/vmaf/model/vmaf_v0.6.1.json",
    "./models/vmaf/vmaf_v0.6.1.json",
    "services/compress/models/vmaf/vmaf_v0.6.1.json"
]

print("\n📋 Checking Default VMAF model locations:")
default_vmaf_found = None
for path in default_vmaf_paths:
    exists = os.path.exists(path)
    status = "✅" if exists else "❌"
    print(f"   {status} {path}")
    if exists and not default_vmaf_found:
        default_vmaf_found = path

print("\n" + "=" * 80)
print("Summary:")
print("=" * 80)

if vmafneg_found:
    print(f"✅ VMAFNEG model found at: {vmafneg_found}")
    print(f"\n   Use this in your config:")
    print(f"   'vmafneg_model': '{vmafneg_found}'")
else:
    print("❌ VMAFNEG model NOT found!")
    print("\n   To install:")
    print("   1. Download from: https://github.com/Netflix/vmaf/tree/master/model")
    print("   2. Place in: /usr/local/share/vmaf/model/")
    print("   3. Or use libvmaf's default model (less accurate)")

if default_vmaf_found:
    print(f"\n✅ Default VMAF model found at: {default_vmaf_found}")
else:
    print("\n⚠️ Default VMAF model not found (will use libvmaf default)")

print("\n" + "=" * 80)
print("Recommendation:")
print("=" * 80)

if vmafneg_found:
    print("✅ Use VMAFNEG model for Netflix per-title encoding")
    print("   This matches what validators use for scoring")
    print(f"\n   Config:")
    print(f"   'use_vmafneg': True")
    print(f"   'vmafneg_model': '{vmafneg_found}'")
else:
    print("⚠️ VMAFNEG model not available")
    print("   You can still use default VMAF model, but scores may differ from validators")
    if default_vmaf_found:
        print(f"\n   Config:")
        print(f"   'use_vmafneg': False")
        print(f"   'default_vmaf_model': '{default_vmaf_found}'")
    else:
        print(f"\n   Config:")
        print(f"   'use_vmafneg': False")
        print(f"   'default_vmaf_model': None  # Will use libvmaf default")

print("\n" + "=" * 80)

