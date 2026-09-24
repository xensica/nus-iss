"""Strict daily-aggregate CSV inputs. No customer identifiers are needed."""
import csv
import hashlib
import io
import random
from datetime import date, timedelta

PRODUCTS = [
    ('COF', 'Cold brew coffee', 'Drinks', 34, 200),
    ('TEA', 'Jasmine green tea', 'Drinks', 29, 140),
    ('WAT', 'Mineral water', 'Drinks', 47, 80),
    ('OAT', 'Oat milk', 'Chilled', 18, 290),
    ('JUI', 'Orange juice', 'Chilled', 23, 230),
    ('BAR', 'Granola bar', 'Snacks', 27, 120),
    ('NUT', 'Roasted almonds', 'Snacks', 16, 250),
    ('CRK', 'Rice crackers', 'Snacks', 20, 150),
    ('CHO', 'Dark chocolate', 'Snacks', 14, 280),
    ('NOO', 'Instant noodles', 'Pantry', 24, 130),
    ('BIS', 'Butter biscuits', 'Pantry', 17, 190),
    ('HON', 'Honey sachets', 'Pantry', 12, 90),
]


def sample_data(as_of=date(2026, 9, 24)):
    sales, inventory = [], []
    for i, (pid, name, category, base, price) in enumerate(PRODUCTS):
        rng = random.Random(420+i)
        for ago in range(84, 0, -1):
            d = as_of-timedelta(days=ago)
            units = max(0, round(base*(1.25 if d.weekday() >= 5 else 1)*rng.uniform(.88, 1.12)))
            sales.append(dict(date=d.isoformat(), product_id=pid, units=units))
        cover = [4, 6, 3, 9, 5, 8, 19, 4, 12, 7, 20, 5][i]
        inventory.append(dict(product_id=pid, name=name, category=category,
            current_stock=base*cover, incoming_units=base*3 if i in (3, 8) else 0,
            incoming_day=5, unit_price_cents=price))
    return assemble(sales, inventory, 'Simulated sample • 12 products')


def csv_text(rows):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    # Spreadsheet exports must not interpret uploaded labels as formulas.
    writer.writerows({k:("'"+v if isinstance(v,str) and v.startswith(('=','+','-','@','\t','\r')) else v) for k,v in row.items()} for row in rows)
    return stream.getvalue()


def _rows(blob, required, label):
    if hasattr(blob, 'read'):
        blob = blob.read()
    if isinstance(blob, bytes):
        if len(blob) > 10_000_000:
            raise ValueError(f'{label}: maximum file size is 10 MB.')
        try:
            blob = blob.decode('utf-8-sig')
        except UnicodeDecodeError:
            raise ValueError(f'{label}: save the file as UTF-8 CSV.') from None
    try:
        reader = csv.DictReader(io.StringIO(blob), strict=True)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or not set(required).issubset(fields):
            raise ValueError(f'{label}: use unique columns including {", ".join(required)}.')
        rows = list(reader)
    except (csv.Error, TypeError):
        raise ValueError(f'{label}: malformed CSV.') from None
    if not rows or len(rows)>100_000:
        raise ValueError(f'{label}: provide 1–100,000 rows.')
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError(f'{label}: some rows have the wrong number of columns.')
    return rows


def _integer(value, column, row, maximum=1_000_000):
    try:
        # Deliberately reject fractions, NaN, scientific notation and negatives.
        if not str(value).strip().isascii() or not str(value).strip().isdigit():
            raise ValueError()
        number = int(value)
        if number > maximum:
            raise ValueError()
        return number
    except (ValueError, TypeError):
        raise ValueError(f'Row {row}: {column} must be a whole number from 0 to {maximum}.') from None


def _id(value, row):
    value = value.strip()
    if not value or len(value)>40 or not all(c.isascii() and (c.isalnum() or c in '-_') for c in value):
        raise ValueError(f'Row {row}: product_id must use 1–40 letters, digits, hyphens or underscores.')
    return value


def load_sales(blob):
    result, seen = [], set()
    for n, row in enumerate(_rows(blob, ['date','product_id','units'], 'Sales'), 2):
        pid = _id(row['product_id'], n)
        try:
            d = date.fromisoformat(row['date']).isoformat()
            if d != row['date']:
                raise ValueError()
        except ValueError:
            raise ValueError(f'Row {n}: date must use YYYY-MM-DD.') from None
        if (pid, d) in seen:
            raise ValueError(f'Row {n}: duplicate product/date. Aggregate transactions to daily totals first.')
        seen.add((pid, d))
        result.append(dict(date=d, product_id=pid, units=_integer(row['units'], 'units', n)))
    return result


def load_inventory(blob):
    result, seen = [], set()
    for n, row in enumerate(_rows(blob, ['product_id','current_stock'], 'Inventory'), 2):
        pid = _id(row['product_id'], n)
        if pid in seen:
            raise ValueError(f'Row {n}: duplicate inventory product.')
        seen.add(pid)
        incoming = _integer(row.get('incoming_units') or '0','incoming_units',n)
        day = _integer(row.get('incoming_day') or ('0' if incoming else '1'),'incoming_day',n,14)
        if day<1:
            raise ValueError(f'Row {n}: incoming_day must be 1–14.')
        price = _integer(row.get('unit_price_cents') or '200','unit_price_cents',n,100000)
        if price == 0:
            raise ValueError(f'Row {n}: unit_price_cents must be positive.')
        result.append(dict(product_id=pid, name=(row.get('name') or pid)[:100],
            category=(row.get('category') or 'Imported')[:60],
            current_stock=_integer(row['current_stock'],'current_stock',n),
            incoming_units=incoming, incoming_day=day, unit_price_cents=price))
    if len(result)>15:
        raise ValueError('This prototype supports up to 15 products per import.')
    return result


def assemble(sales, inventory, source):
    ids = {p['product_id'] for p in inventory}
    if ids != {s['product_id'] for s in sales}:
        raise ValueError('Sales and inventory must contain the same product IDs. No data was imported.')
    products=[]
    for row in inventory:
        records=sorted([dict(date=r['date'],units=r['units']) for r in sales if r['product_id']==row['product_id']], key=lambda r:r['date'])
        products.append(dict(row, history=records))
    fingerprint=hashlib.sha256(csv_text(sales).encode()+csv_text(inventory).encode()).hexdigest()[:16]
    return dict(products=products, source=source, fingerprint=fingerprint, sales=sales, inventory=inventory)


def load_dataset(sales_blob, inventory_blob):
    return assemble(load_sales(sales_blob),load_inventory(inventory_blob),'Uploaded CSV • user-provided data')
