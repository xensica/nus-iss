"""Prepare a UCI-format transaction CSV without retaining customer identifiers.

Source schema: https://archive.ics.uci.edu/dataset/352/online+retail
Input must be a complete transaction ledger for the imported observation interval.
Original sale prices are GBP and are NOT used as simulated SGD purchase prices.
"""
import io
import math
import pandas as pd
from .data_io import assemble


def prepare_uci(blob, date_format='%m/%d/%Y %H:%M', count=12, max_transaction_units=1000):
    if len(blob)>100_000_000: raise ValueError('Transaction CSV must be under 100 MB.')
    columns=['InvoiceNo','StockCode','Description','Quantity','InvoiceDate','UnitPrice']
    try:
        frame=pd.read_csv(io.BytesIO(blob),usecols=columns,dtype={'InvoiceNo':'string','StockCode':'string','Description':'string'})
    except Exception:
        raise ValueError('Use a UTF-8 UCI transaction CSV with InvoiceNo, StockCode, Description, Quantity, InvoiceDate and UnitPrice.') from None
    initial=len(frame)
    cancelled=frame['InvoiceNo'].str.upper().str.startswith('C',na=False)
    q=pd.to_numeric(frame['Quantity'],errors='coerce')
    price=pd.to_numeric(frame['UnitPrice'],errors='coerce')
    dates=pd.to_datetime(frame['InvoiceDate'],format=date_format,errors='coerce')
    valid=(~cancelled & q.gt(0) & q.le(max_transaction_units) & (q%1).eq(0) & price.gt(0) & price.lt(float('inf')) & dates.notna() & frame[columns].notna().all(axis=1) & frame['StockCode'].str.fullmatch(r'[A-Za-z0-9_-]{1,40}',na=False))
    frame=frame.loc[valid].copy()
    frame['units']=q[valid].astype(int); frame['date']=dates[valid].dt.normalize()
    if frame.empty: raise ValueError('No valid transactions remain. Check the date format and cleaning policy.')
    end=frame['date'].max()
    train=frame[frame['date']<=end-pd.Timedelta(days=14)]
    ids=train.groupby('StockCode')['date'].nunique().sort_values(ascending=False).head(count).index
    if len(ids)==0: raise ValueError('Provide more than 14 days of transactions.')
    sales,inventory=[],[]
    for pid in ids:
        product=frame[frame['StockCode']==pid]
        first=product['date'].min()
        if (end-first).days<41: continue
        daily=product.groupby('date')['units'].sum().reindex(pd.date_range(first,end),fill_value=0)
        sales.extend(dict(date=d.date().isoformat(),product_id=str(pid),units=int(n)) for d,n in daily.items())
        avg=float(daily.tail(28).mean())
        inventory.append(dict(product_id=str(pid),name=str(product['Description'].iloc[0])[:100],category='UCI retail',
            current_stock=math.ceil(avg*5),incoming_units=0,incoming_day=1,unit_price_cents=200))
    if not inventory: raise ValueError('Selected products need at least 42 calendar days of observations.')
    dataset=assemble(sales,inventory,'UCI-format upload • sales supplied by user; simulated stock & suppliers')
    dataset['cleaning']=dict(input_rows=initial,retained_rows=len(frame),excluded_rows=initial-len(frame),cancelled_rows=int(cancelled.sum()),
        selected_products=len(inventory),max_transaction_units=max_transaction_units,
        date_format=date_format,analysis_date=end.date().isoformat(),
        assumptions='Complete ledger assumed: no-sale dates from first transaction to end are filled with zero. Products chosen by training-period trading-day coverage, not holdout performance. Nonpositive prices/quantities, cancellations, missing required values, invalid dates/codes and quantities above the explicit transaction cap excluded. Returns are excluded, not netted. Customer identifiers never retained. Inventory is simulated at five days of recent mean; SGD purchase reference price fixed at 200 cents, not converted from GBP. Cleaning may exclude legitimate bulk orders.')
    return dataset
