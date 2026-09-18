"""Cập nhật giá ba sàn, giữ lịch sử và xuất dữ liệu cho Alpha Stock."""
import gzip
import io
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from vnstock import Listing, Quote

DATA = Path('price-cache')
SITE = Path('site')
COLS = ['ticker', 'exchange', 'sector', 'date', 'open', 'high', 'low', 'close', 'volume']
NOW = datetime.now(ZoneInfo('Asia/Ho_Chi_Minh'))
SMOKE = os.environ.get('TEST_ONLY', 'false').lower() == 'true'


def normalize(raw, symbol, exchange):
    """Nguồn KBS trả giá cổ phiếu theo nghìn đồng, chỉ số theo điểm."""
    if raw is None or raw.empty:
        raise ValueError('Nguồn trả dữ liệu rỗng')
    result = raw.rename(columns={'time': 'date'}).copy()
    result['date'] = pd.to_datetime(result['date']).dt.strftime('%Y-%m-%d')
    result['ticker'], result['exchange'], result['sector'] = symbol, exchange, 'Chưa phân loại'
    numeric = ['open', 'high', 'low', 'close', 'volume']
    result[numeric] = result[numeric].apply(pd.to_numeric, errors='coerce')
    if exchange != 'INDEX':
        result[['open', 'high', 'low', 'close']] *= 1000
    result = result.dropna(subset=numeric)
    result = result[(result['close'] > 0) & (result['volume'] >= 0) & (result['high'] >= result['low']) & (result['date'] <= NOW.date().isoformat())]
    if result.empty:
        raise ValueError('Không có dòng giá hợp lệ')
    return result[COLS].drop_duplicates(['ticker', 'date']).sort_values('date')


def main():
    DATA.mkdir(exist_ok=True)
    old_path = DATA / 'market.csv.gz'
    if not old_path.exists() and not SMOKE:
        try:
            response = requests.get('https://kalm-d.github.io/alpha-stock/data/market.csv.gz', timeout=45)
            if response.ok:
                pd.read_csv(io.BytesIO(gzip.decompress(response.content)))
                old_path.write_bytes(response.content)
        except Exception:
            print('Chưa có lịch sử đã xuất bản; bắt đầu tải lần đầu.', flush=True)
    old = pd.read_csv(old_path, dtype={'ticker': str, 'date': str}) if old_path.exists() else pd.DataFrame(columns=COLS)
    universe = Listing(source='KBS').symbols_by_exchange()
    required = {'symbol', 'exchange', 'type'}
    if not required.issubset(universe.columns):
        raise RuntimeError('Không lấy được danh sách sàn chính xác')
    universe = universe[universe['type'].eq('stock') & universe['exchange'].isin(['HOSE', 'HNX', 'UPCOM'])].drop_duplicates('symbol')
    if set(universe['exchange']) != {'HOSE', 'HNX', 'UPCOM'}:
        raise RuntimeError('Danh sách nguồn thiếu một trong ba sàn')
    if SMOKE:
        universe = universe.groupby('exchange').head(1)
    tasks = [('VNINDEX', 'INDEX')] + list(universe[['symbol', 'exchange']].itertuples(index=False, name=None))
    groups = {symbol: rows for symbol, rows in old.groupby('ticker')}
    errors, success = [], 0
    for index, (symbol, exchange) in enumerate(tasks, 1):
        previous = groups.get(symbol, pd.DataFrame(columns=COLS))
        start = (NOW.date() - timedelta(days=700)).isoformat()
        if not previous.empty and NOW.weekday() != 0:
            start = (pd.Timestamp(previous['date'].max()).date() - timedelta(days=10)).isoformat()
        try:
            raw = None
            for attempt in range(3):
                try:
                    time.sleep(3.6)
                    raw = Quote(symbol=symbol, source='KBS').history(start=start, end=NOW.date().isoformat(), interval='1D')
                    break
                except (Exception, SystemExit):
                    if attempt == 2:
                        raise RuntimeError('Nguồn không trả dữ liệu sau ba lần thử')
                    time.sleep(70)
            fresh = normalize(raw, symbol, exchange)
            # Phát hiện lịch sử bị điều chỉnh để tải lại toàn bộ mã.
            if not previous.empty and start != (NOW.date() - timedelta(days=700)).isoformat():
                overlap = previous.merge(fresh, on='date', suffixes=('_old', '_new'))
                settled = overlap[overlap['date'] < previous['date'].max()]
                if not settled.empty and ((settled['close_old'] - settled['close_new']).abs() > 0.01).any():
                    time.sleep(3.6)
                    fresh = normalize(Quote(symbol=symbol, source='KBS').history(start=(NOW.date()-timedelta(days=700)).isoformat(), end=NOW.date().isoformat(), interval='1D'), symbol, exchange)
                    previous = pd.DataFrame(columns=COLS)
            groups[symbol] = pd.concat([previous, fresh], ignore_index=True).drop_duplicates(['ticker', 'date'], keep='last').sort_values('date').tail(320)
            success += 1
        except (Exception, SystemExit) as exc:
            errors.append({'ticker': symbol, 'reason': str(exc)[:160]})
        if index % 50 == 0:
            pd.concat(list(groups.values()), ignore_index=True).to_csv(old_path, index=False, compression='gzip')
        print(f'{index}/{len(tasks)} {symbol}: thành công {success}, lỗi {len(errors)}', flush=True)
    if success < len(tasks) * 0.8 or 'VNINDEX' not in groups:
        raise RuntimeError('Chất lượng tải không đủ: giữ nguyên website đã xuất bản')
    wanted = {symbol for symbol, _ in tasks}
    result = pd.concat([rows for symbol, rows in groups.items() if symbol in wanted], ignore_index=True)
    if set(result['exchange']) != {'HOSE', 'HNX', 'UPCOM', 'INDEX'}:
        raise RuntimeError('Dữ liệu kết quả không đủ ba sàn và chỉ số')
    if SMOKE:
        print('Kiểm tra nguồn ba sàn và VNINDEX thành công; không xuất bản dữ liệu thử.')
        return
    result.to_csv(old_path, index=False, compression='gzip')
    target = SITE / 'data'
    target.mkdir(parents=True, exist_ok=True)
    (target / 'market.csv.gz').write_bytes(old_path.read_bytes())
    latest = result.groupby(['ticker', 'exchange'])['date'].max().reset_index()
    meta = {'updated_at': datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).isoformat(), 'scheduled_time': '15:00 Asia/Ho_Chi_Minh, thứ Hai–thứ Sáu', 'source': 'Vnstock / KBS', 'latest_date': str(latest['date'].max()), 'oldest_ticker_date': str(latest['date'].min()), 'tickers': int(len(latest)), 'successful': success, 'failed': errors, 'exchanges': latest.groupby('exchange').size().to_dict(), 'same_day_tickers': int(latest['date'].eq(NOW.date().isoformat()).sum()), 'note': 'Bắt đầu tải lúc 15:00; dữ liệu có thể chưa chốt cuối phiên. Mã tải lỗi được giữ bản cũ nếu có.'}
    (target / 'status.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in meta.items() if k != 'failed'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
