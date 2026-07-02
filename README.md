# WH Pallet Printer

Windows desktop app for warehouse pallet label printing.

## Features

- Enter Art Num + cartons to print a table: Art Num | Cartons | Qty | Barcode
- Qty = Cartons x Qty/Carton (from local article data)
- Code 128 barcodes wedge-scan as: Art Num, Enter, Qty
- Import/export article Qty/Carton data via Excel

## Development

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\activate
pip install -r requirements.txt
python scripts/seed_data.py
python run_dev.py
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 (Vite proxies `/api` to port 8766).

## Windows build

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
powershell -ExecutionPolicy Bypass -File .\build_installer.ps1 -Version 1.0.0
```
