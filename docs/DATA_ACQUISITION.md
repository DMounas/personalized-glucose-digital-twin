# Data Acquisition Guide: CGMacros v1.0.0

This guide provides instructions for acquiring, verifying, and preparing the CGMacros dataset (PhysioNet v1.0.0) for use with this repository.

> **CRITICAL REMINDER**: All contents of the `data/` directory, ZIP archives, and raw image files are strictly excluded via `.gitignore`. Never commit raw data files, archives, or meal photographs to version control.

---

## 1. Obtaining the Dataset
The CGMacros dataset is hosted openly on PhysioNet at:
[https://physionet.org/content/cgmacros/1.0.0/](https://physionet.org/content/cgmacros/1.0.0/)

Three supported acquisition methods are available:

### Option A: Direct Web Browser Download
1. Navigate to the PhysioNet dataset landing page: [https://physionet.org/content/cgmacros/1.0.0/](https://physionet.org/content/cgmacros/1.0.0/)
2. Scroll to the **Files** section at the bottom of the page.
3. Download the following primary files to your local `data/` folder:
   - `CGMacros_dateshifted365.zip` (Main participant archive, ~626.7 MB)
   - `DataDictionary_CGMacros-00X.csv`
   - `DataDictionary_Bio.csv`
   - `DataDictionary_Gut_Health_Test.csv`
   - `DataDictionary_Microbes.csv`
   - `SHA256SUMS.txt`

### Option B: Terminal Download via `wget` (Linux / macOS)
From the project root directory:
```bash
mkdir -p data/cgmacros
wget -r -N -c -np -nH --cut-dirs=3 \
  -P data/cgmacros \
  https://physionet.org/files/cgmacros/1.0.0/
```

### Option C: AWS CLI / S3 Sync (Cross-Platform)
PhysioNet provides public access via AWS Open Data without requiring AWS credentials:

#### Linux / macOS:
```bash
mkdir -p data/cgmacros
aws s3 sync --no-sign-request s3://physionet-open/cgmacros/1.0.0/ data/cgmacros/
```

#### Windows PowerShell:
```powershell
New-Item -ItemType Directory -Force -Path "data\cgmacros"
aws s3 sync --no-sign-request s3://physionet-open/cgmacros/1.0.0/ data\cgmacros\
```

---

## 2. Manual Archive Extraction
The primary dataset payload is contained inside `CGMacros_dateshifted365.zip`. The audit tool **never silently extracts archives**, adhering strictly to safe read-only principles. You must extract the archive manually.

### Linux / macOS:
```bash
cd data/cgmacros
unzip CGMacros_dateshifted365.zip
```

### Windows PowerShell:
```powershell
Expand-Archive -Path "data\cgmacros\CGMacros_dateshifted365.zip" -DestinationPath "data\cgmacros"
```

---

## 3. Verifying Integrity Against SHA256SUMS.txt
The downloaded dataset includes an official `SHA256SUMS.txt` cryptographic manifest. You can verify downloaded file hashes using the built-in audit tooling.

### Windows PowerShell:
```powershell
python -m dtwin.audit --data-dir data\cgmacros --verify-checksums
```

### Linux / macOS:
```bash
python -m dtwin.audit --data-dir data/cgmacros --verify-checksums
```

The tool will stream and calculate SHA-256 digests for all present files and output a verification section in `docs/reports/audit_report.md` and `docs/reports/audit_report.json` reporting match, mismatch, and missing counts without halting execution.

---

## 4. Expected Directory Shape (General Terms)
After extraction, your `data/` directory will generally resemble the following structure (note that the audit tool dynamically profiles the real structure without hardcoded filename assumptions):

```
data/cgmacros/
├── SHA256SUMS.txt
├── DataDictionary_Bio.csv
├── DataDictionary_CGMacros-00X.csv
├── DataDictionary_Gut_Health_Test.csv
├── DataDictionary_Microbes.csv
├── bio.csv
├── gut_health_test.csv
├── microbes.csv (or microbs.csv)
├── CGMacros-001/
│   ├── CGMacros-001.csv
│   └── photos/
│       ├── meal1_before.jpg
│       └── meal1_after.jpg
└── CGMacros-002/
    ├── CGMacros-002.csv
    └── photos/
```
